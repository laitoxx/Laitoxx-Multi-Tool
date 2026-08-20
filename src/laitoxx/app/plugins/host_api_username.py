"""
Lua Plugin Engine for Laitoxx.

Uses `lupa` (LuaJIT/Lua runtime for Python) to execute Lua plugins
inside a sandboxed environment with a rich host API.
"""

from laitoxx.shared.graph.model import Edge, Node

from .lua_values import _lua_str, _python_to_lua


class UsernameHostMixin:
    def username_search(self, username, categories=None, max_workers=30):
        """Search username across sites. Returns results as Lua table.

        Usage in Lua::

            local results = host:username_search("johndoe")
            -- or with category filter:
            local results = host:username_search("johndoe", {"social", "gaming"})
        """
        from laitoxx.features.osint.username_osint.checker import UsernameChecker
        from laitoxx.features.osint.username_osint.site_db import SiteDB

        db = SiteDB()
        sites = db.load()
        if categories and hasattr(categories, "values"):
            cat_list = [_lua_str(v) for v in categories.values()]
            sites = db.filter_by_category(cat_list)

        self._output(f"[Username OSINT] Checking '{_lua_str(username)}' on {len(sites)} sites...")

        def _progress(checked, total, result):
            if result.is_found:
                self._output(f"  [+] {result.site_name}: {result.url}")

        checker = UsernameChecker(
            sites,
            max_workers=int(max_workers),
            progress_callback=_progress,
        )
        results = checker.check_username(_lua_str(username))

        # Convert to Lua table
        out = {}
        for i, r in enumerate([x for x in results if x.is_found], 1):
            out[i] = {
                "site": r.site_name,
                "url": r.url,
                "category": r.category,
                "http_code": r.http_code or 0,
                "response_ms": round(r.response_time_ms),
            }
            if r.avatar_url:
                out[i]["avatar_url"] = r.avatar_url

        self._output(f"[Username OSINT] Found {len(out)} accounts.")
        return _python_to_lua(self._lua, out)

    def username_generate_nicks(self, username, max_variants=100, first_name=None, last_name=None):
        """Generate forensic nickname variants. Returns Lua table of strings.

        Usage in Lua::

            local nicks = host:username_generate_nicks("johndoe", 50)
            for i, nick in ipairs(nicks) do print(nick) end
        """
        from laitoxx.features.osint.username_osint.nickname_generator import (
            NicknameGenerator,
        )

        gen = NicknameGenerator(_lua_str(username), max_variants=int(max_variants))
        variants = gen.generate_all(
            first_name=_lua_str(first_name) if first_name else "",
            last_name=_lua_str(last_name) if last_name else "",
        )

        self._output(f"[Nickname Gen] Generated {len(variants)} variants for '{_lua_str(username)}'")
        return _python_to_lua(self._lua, variants)

    def username_search_to_graph(self, graph_id, username, categories=None):
        """Search username and auto-populate a graph with results.

        Usage in Lua::

            local gid = host:graph_create("OSINT Graph")
            host:username_search_to_graph(gid, "johndoe")
        """
        from laitoxx.features.osint.username_osint.checker import UsernameChecker
        from laitoxx.features.osint.username_osint.models import CATEGORY_ICONS
        from laitoxx.features.osint.username_osint.site_db import SiteDB

        g = self._get_graph(graph_id)
        if g is None:
            return None, f"Graph '{graph_id}' not found"

        uname = _lua_str(username)

        # Run search
        db = SiteDB()
        sites = db.load()
        if categories and hasattr(categories, "values"):
            cat_list = [_lua_str(v) for v in categories.values()]
            sites = db.filter_by_category(cat_list)

        self._output(f"[Username→Graph] Checking '{uname}' on {len(sites)} sites...")
        checker = UsernameChecker(sites, max_workers=30)
        results = checker.check_username(uname)
        found = [r for r in results if r.status == "found"]

        if not found:
            self._output(f"[Username→Graph] No accounts found for '{uname}'.")
            return 0

        # Build graph nodes
        central = Node.from_type(f"@{uname}", "Username")
        g.add_node(central)

        cat_nodes = {}
        for r in found:
            cat = r.category
            if cat not in cat_nodes:
                icon = CATEGORY_ICONS.get(cat, "")
                cn = Node.from_type(f"{icon} {cat.capitalize()}", "Category")
                g.add_node(cn)
                g.add_edge(Edge(central.id, cn.id, label=cat, edge_type="BelongsToCategory"))
                cat_nodes[cat] = cn

            sn = Node.from_type(r.site_name, "SocialAccount")
            sn.description = r.url
            sn.metadata = {"url": r.url}
            g.add_node(sn)
            g.add_edge(
                Edge(
                    cat_nodes[cat].id,
                    sn.id,
                    label="registered",
                    edge_type="RegisteredOn",
                )
            )

        self._output(f"[Username→Graph] Added {len(found)} sites + {len(cat_nodes)} categories to graph.")
        return len(found)
