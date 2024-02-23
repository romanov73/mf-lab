from frc import DocxReport


if __name__ == "__main__":
    file = DocxReport()

    context = {
        "variables": [
            {
                "name": "Test1",
                "value": 1.23
            },
            {
                "name": "Test2",
                "value": 1.2321
            },
            {
                "name": "Test3",
                "value": 1
            },
        ],
        "formula": "Test1 + Test2 + Test3",
        "result": 1.23 + 1.2321 + 1
    }
    file.render(context)
    file.save("test.docx")



