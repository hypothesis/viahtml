def environment_variables():
    return {
        "VIA_H_EMBED_URL": "http://localhost:3001/hypothesis",
        "VIA_IGNORE_PREFIXES": ",".join(
            [
                "http://localhost:5000/",
                "http://localhost:3001/",
                "https://localhost:5000/",
                "https://localhost:3001/",
            ]
        ),
        "VIA_DEBUG": "1",
        "VIA_BLOCKLIST_FILE": "../conf/blocklist-dev.txt",
    }
