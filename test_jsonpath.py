from app.utils.parser import extract_by_json_path

test_data = {
    "answer": [
        {
            "txt": [
                {
                    "content": {
                        "components": [
                            {
                                "data": {
                                    "datas": [1, 2, 3]
                                }
                            }
                        ]
                    }
                }
            ]
        }
    ]
}

cases = [
    ("answer[0].txt[0].content.components[0].data.datas", [1, 2, 3]),
    ("answer[0].txt[0].content.components[1]", None),
    ("x.y", None),
    ("", test_data),
    ("answer[0]", test_data["answer"][0])
]

for path, expected in cases:
    result = extract_by_json_path(test_data, path)
    print(f"Path: {path}")
    print(f"Expected: {expected}")
    print(f"Result: {result}")
    print(f"Match: {result == expected}")
    print("-" * 20)
