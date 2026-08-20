"""Execution pipeline for user-defined plugins."""

from __future__ import annotations

import contextlib
import io
import logging
import os
import platform
import re
import subprocess
import sys
import time

from .worker_io import _InputOverride, remove_ansi_codes


class PluginExecutionMixin:
    def _run_plugin(self):
        plugin_data = self.func
        outputs = {}
        try:
            system = platform.system().lower()
            supported_os_list = [s.lower() for s in plugin_data.get("supported_os", [])]
            if supported_os_list and not any(s in system for s in supported_os_list):
                self.error.emit(
                    f"Plugin Error: OS Not Supported. Supports {supported_os_list}, but you are on {system}."
                )
                return

            steps = plugin_data.get("steps", [])
            steps_by_id = {step.get("id"): step for step in steps if "id" in step}
            sorted_steps = sorted(steps, key=lambda x: x.get("order", 0))

            step_index = 0
            while step_index < len(sorted_steps):
                if self._cancel_event.is_set():
                    self.error.emit("Execution cancelled by user.")
                    return
                step = sorted_steps[step_index]
                step_id = step.get("id", f"step_{step_index + 1}")
                description = step.get("description", "Unnamed Step")
                self.update.emit(f"--- Running Step {step_index + 1}: {description} ---")

                step_successful = False
                step_output = ""

                if step.get("type") == "delay":
                    duration = step.get("duration", 1)
                    self.update.emit(f"Delaying for {duration} second(s)...")
                    time.sleep(duration)
                    step_output = f"Delayed for {duration}s"
                    step_successful = True
                else:
                    current_input = self._resolve_input(step, outputs)
                    step_successful, step_output = self._execute_step(step, current_input, plugin_data)
                    if step_output is None:
                        return  # fatal error already emitted

                outputs[step_id] = step_output

                next_step_id = None
                if step_successful:
                    if "on_success" in step:
                        next_step_id = step["on_success"]
                        self.update.emit(f"Step successful. Jumping to step '{next_step_id}'.")
                else:
                    if "on_failure" in step:
                        next_step_id = step["on_failure"]
                        self.update.emit(f"Step failed. Jumping to step '{next_step_id}'.")
                    else:
                        self.error.emit(f"Execution halted due to failed step: {description}")
                        return

                if next_step_id:
                    if next_step_id in steps_by_id:
                        target_step = steps_by_id[next_step_id]
                        try:
                            step_index = sorted_steps.index(target_step)
                        except ValueError:
                            self.error.emit(f"FATAL: Could not find jump target step '{next_step_id}'.")
                            return
                    else:
                        self.error.emit(f"Error: Jump target step ID '{next_step_id}' not found.")
                        return
                else:
                    step_index += 1

        except Exception as e:
            logging.error(f"Error executing plugin {plugin_data.get('name')}: {e}", exc_info=True)
            self.error.emit(f"A critical error occurred in the plugin executor: {e}")
        finally:
            self.finished.emit()

    def _emit_update(self, msg: str):
        if self._cancel_event.is_set():
            return
        self.update.emit(msg)

    def _resolve_input(self, step, outputs):
        input_source = step.get("input_source", "none")
        if input_source == "user":
            return self.input_data or ""
        if input_source.startswith("previous_step:"):
            source_step_id = input_source.split(":", 1)[1]
            previous_output = outputs.get(source_step_id, "")
            regex_filters = step.get("input_filter_regexes", [])
            if not regex_filters and "input_filter_regex" in step:
                regex_filters = [step["input_filter_regex"]]
            if regex_filters:
                all_matches = []
                for regex_filter in regex_filters:
                    if not regex_filter:
                        continue
                    try:
                        matches = re.findall(regex_filter, previous_output)
                        all_matches.extend(matches)
                        self.update.emit(f"Applied REGEX '{regex_filter}'. Found {len(matches)} match(es).")
                    except re.error as e:
                        self.error.emit(f"Error in REGEX pattern '{regex_filter}': {e}")
                        return ""
                return "\n".join(all_matches)
            return previous_output
        return ""

    def _execute_step(self, step, current_input, plugin_data):
        action_type = step.get("action_type", "command")
        action_value = step.get("action_value", "")
        plugin_path = plugin_data.get("plugin_path", ".")

        if action_type in ("command", "batch_script", "shell_script"):
            return self._run_shell_step(step, action_type, action_value, current_input, plugin_path)
        if action_type == "python_script":
            return self._run_python_script_step(action_value, current_input, plugin_path)
        if action_type == "function":
            return self._run_function_step(action_value, current_input)
        return False, ""

    def _run_shell_step(self, step, action_type, action_value, current_input, plugin_path):
        script_path = os.path.join(plugin_path, action_value)
        if action_type == "command":
            command = action_value.replace("{input}", current_input)
        else:
            if not os.path.isfile(script_path):
                self.error.emit(f"Error: {action_type.replace('_', ' ').title()} '{action_value}' not found.")
                return False, ""
            command = script_path.replace("{input}", current_input)

        sanitized = command
        if step.get("requires_api_key"):
            api_key = step.get("api_key", "")
            command = command.replace("{AKEY}", api_key)
            sanitized = sanitized.replace("{AKEY}", "********")

        self.update.emit(f"Executing {action_type.replace('_', ' ')}: {sanitized}")

        if action_type == "batch_script" and platform.system() == "Windows":
            command = f'cmd /c "{command}"'
        elif action_type == "shell_script" and platform.system() != "Windows":
            command = f'sh "{command}"'

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        if result.stdout.strip():
            self.update.emit(f"STDOUT:\n{result.stdout.strip()}")
        if result.returncode != 0:
            if result.stderr.strip():
                self.update.emit(f"STDERR:\n{result.stderr.strip()}")
            self.error.emit(f"Error: Step failed with exit code {result.returncode}.")
            return False, result.stdout.strip()
        return True, result.stdout.strip()

    def _run_python_script_step(self, action_value, current_input, plugin_path):
        script_path = os.path.join(plugin_path, action_value)
        if not os.path.isfile(script_path):
            self.error.emit(f"Error: Python script '{action_value}' not found.")
            return False, ""
        self.update.emit(f"Executing Python script: {action_value}")
        result = subprocess.run(
            [sys.executable, script_path],
            input=current_input,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        if result.stdout.strip():
            self.update.emit(f"STDOUT:\n{result.stdout.strip()}")
        if result.returncode != 0:
            if result.stderr.strip():
                self.update.emit(f"STDERR:\n{result.stderr.strip()}")
            self.error.emit(f"Error: Script failed with exit code {result.returncode}.")
            return False, result.stdout.strip()
        return True, result.stdout.strip()

    def _run_function_step(self, action_value, current_input):
        if not self.tool_info or action_value not in self.tool_info:
            self.error.emit(f"Error: Built-in function '{action_value}' not found.")
            return False, ""
        tool_func = self.tool_info[action_value].get("func")
        self.update.emit(f"Executing function: {action_value} with input: '{current_input[:50]}...'")
        output_stream = io.StringIO()
        try:
            with (
                _InputOverride(current_input or ""),
                contextlib.redirect_stdout(output_stream),
            ):
                tool_func()
            step_output = remove_ansi_codes(output_stream.getvalue().strip())
            self.update.emit(f"Output:\n{step_output}")
            return True, step_output
        except Exception as e:
            self.error.emit(f"Error executing function '{action_value}': {e}")
            logging.error(f"Error in plugin function {action_value}: {e}", exc_info=True)
            return False, ""
