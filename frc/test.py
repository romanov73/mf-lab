from frc import DocxReport


TEST_BINARY = True


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

    if TEST_BINARY:
        file_stream = file.get_bytes_array()
        bytes_arr = file_stream.read()
        print(bytes_arr)
        with open("test.docx", "wb") as f:
            f.write(bytes_arr)
    else:
        file.save("test.docx")



