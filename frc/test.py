from frc import DocxReport
import io

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
        print(list(file_stream))
        with open("test.docx", "wb") as f:
            f.write(file_stream.read())
    else:
        file.save("test.docx")



