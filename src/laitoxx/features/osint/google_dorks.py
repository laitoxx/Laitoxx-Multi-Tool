"""Declarative Google dork operator catalogue."""

OPERATORS = {
    "1": {
        "name": "site",
        "desc": "Search within a specific site/domain. Syntax: site:domain.com",
    },
    "2": {
        "name": "inurl",
        "desc": "Search for URLs containing specific words. Syntax: inurl:word",
    },
    "3": {
        "name": "intext",
        "desc": "Search for pages containing specific text. Syntax: intext:word",
    },
    "4": {
        "name": "intitle",
        "desc": "Search for pages with specific words in title. Syntax: intitle:word",
    },
    "5": {
        "name": "filetype",
        "desc": "Search for specific file types. Syntax: filetype:extension",
    },
    "6": {
        "name": "ext",
        "desc": "Search for files with specific extensions. Syntax: ext:extension",
    },
    "7": {
        "name": "AROUND",
        "desc": "Find documents where words are within N words. Syntax: 'word1' AROUND(n) 'word2'",
    },
    "8": {
        "name": "NEAR",
        "desc": "Similar to AROUND (Bing/SQL/Elasticsearch). Syntax: 'word1' NEAR/n 'word2'",
    },
    "9": {
        "name": "BEFORE",
        "desc": "First word appears before second. Syntax: 'word1' BEFORE 'word2'",
    },
    "10": {
        "name": "AND",
        "desc": "Both words must be present. Syntax: word1 AND word2",
    },
    "11": {
        "name": "OR",
        "desc": "At least one word must be present. Syntax: word1 OR word2",
    },
    "12": {
        "name": "NOT",
        "desc": "Exclude words from results. Syntax: -word or NOT word",
    },
    "13": {
        "name": "exact_phrase",
        "desc": "Search for exact phrase match. Syntax: 'exact phrase here'",
    },
    "14": {
        "name": "grouping",
        "desc": "Group logical conditions. Syntax: (condition1 OR condition2) AND condition3",
    },
    "15": {
        "name": "inanchor",
        "desc": "Search for pages linked with specific anchor text. Syntax: inanchor:'click here'",
    },
    "16": {
        "name": "allinurl",
        "desc": "All specified words must be in URL. Syntax: allinurl:word1 word2",
    },
    "17": {
        "name": "allintitle",
        "desc": "All specified words must be in title. Syntax: allintitle:word1 word2",
    },
    "18": {
        "name": "allintext",
        "desc": "All specified words must be in text. Syntax: allintext:word1 word2",
    },
    "19": {
        "name": "cache",
        "desc": "View Google's cached version of a page. Syntax: cache:example.com",
    },
    "20": {
        "name": "related",
        "desc": "Find pages related to a URL. Syntax: related:example.com",
    },
    "21": {
        "name": "info",
        "desc": "Get information about a URL. Syntax: info:example.com",
    },
    "22": {
        "name": "link",
        "desc": "Find pages that link to a specific URL. Syntax: link:example.com",
    },
    "23": {
        "name": "after",
        "desc": "Search for content after specific date. Syntax: after:YYYY or after:YYYY-MM-DD",
    },
    "24": {
        "name": "before",
        "desc": "Search for content before specific date. Syntax: before:YYYY or before:YYYY-MM-DD",
    },
    "25": {
        "name": "daterange",
        "desc": "Search within date range. Syntax: daterange:start..end",
    },
    "26": {
        "name": "numrange",
        "desc": "Search within a range of numbers. Syntax: numrange:1-100",
    },
    "27": {
        "name": "wildcard_*",
        "desc": "Replace any number of words. Syntax: 'best * ever'",
    },
    "28": {
        "name": "wildcard__",
        "desc": "Replace exactly one word. Syntax: 'best _ in the world'",
    },
    "29": {
        "name": "define",
        "desc": "Get definitions of words. Syntax: define:word",
    },
    "30": {
        "name": "source",
        "desc": "Search news from specific source. Syntax: source:newsoutlet",
    },
    "31": {
        "name": "phonebook",
        "desc": "Search Google phonebook. Syntax: phonebook:John Doe location",
    },
    "32": {"name": "maps", "desc": "Search Google Maps. Syntax: maps:query"},
    "33": {
        "name": "book",
        "desc": "Search Google Books. Syntax: book:title or author",
    },
    "34": {
        "name": "finance",
        "desc": "Search Google Finance. Syntax: finance:stock_symbol",
    },
    "35": {
        "name": "movie",
        "desc": "Search for movie information. Syntax: movie:title",
    },
    "36": {
        "name": "weather",
        "desc": "Search weather information. Syntax: weather:location",
    },
    "37": {
        "name": "stocks",
        "desc": "Search stock information. Syntax: stocks:symbol",
    },
    "38": {
        "name": "location",
        "desc": "Search for location information. Syntax: location:query",
    },
    "39": {
        "name": "feed",
        "desc": "Search for RSS/Atom feeds. Syntax: feed:site.com",
    },
    "40": {"name": "group", "desc": "Search Google Groups. Syntax: group:query"},
    "41": {
        "name": "index_of",
        "desc": "Find open directories. Syntax: intitle:'index of' 'parent directory'",
    },
    "42": {
        "name": "phpinfo",
        "desc": "Find phpinfo.php pages. Syntax: inurl:'/phpinfo.php'",
    },
    "43": {
        "name": "exposed_files",
        "desc": "Find exposed database/config files. Syntax: ext:(sql|db|bak|conf) intext:password",
    },
    "44": {
        "name": "custom",
        "desc": "Enter custom operator or advanced dork manually",
    },
}
