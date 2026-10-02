def search_code(code_analysis, query):
    words = query.lower().replace("?", "").split()

    stop_words = {
        "what", "does", "do", "the", "is",
        "a", "an", "how", "why", "where",
        "this", "that", "function", "class"
    }

    keywords = [
        word for word in words
        if word not in stop_words
    ]

    results = []

    for file_path, data in code_analysis.items():
        matches = []

        for keyword in keywords:
            for function in data.get("functions", []):
                if keyword in function["name"].lower():
                    matches.append({
                        "type": "function",
                        "name": function["name"],
                        "line": function["line"]
                    })

            for cls in data.get("classes", []):
                if keyword in cls["name"].lower():
                    matches.append({
                        "type": "class",
                        "name": cls["name"],
                        "line": cls["line"]
                    })

            for imported in data.get("imports", []):
                if keyword in imported.lower():
                    matches.append({
                        "type": "import",
                        "name": imported
                    })

        if matches:
            results.append({
                "file": file_path,
                "matches": matches,
                "score": len(matches)
            })

    results.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return results