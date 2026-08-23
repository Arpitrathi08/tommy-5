import subprocess
import sys
import time
import webbrowser
import os


BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


BACKEND_DIR = os.path.join(
    BASE_DIR,
    "backend"
)


FRONTEND_DIR = os.path.join(
    BASE_DIR,
    "frontend"
)


def start_backend():

    print(
        "🚀 Starting Tommy backend..."
    )


    command = [

        sys.executable,

        "-m",
        "uvicorn",

        "main:app",

        "--host",
        "127.0.0.1",

        "--port",
        "8000"

    ]


    return subprocess.Popen(
        command,
        cwd=BACKEND_DIR
    )


def start_frontend():

    time.sleep(3)


    index_file = os.path.join(
        FRONTEND_DIR,
        "index.html"
    )


    print(
        "🌐 Opening Tommy..."
    )


    webbrowser.open(
        "file:///" +
        index_file.replace(
            "\\",
            "/"
        )
    )


def main():

    backend = None


    try:

        backend = start_backend()


        start_frontend()


        print("")
        print(
            "=================================="
        )

        print(
            "        TOMMY AI STARTED"
        )

        print(
            "=================================="
        )

        print("")
        print(
            'Say "Hey Tommy"'
        )

        print(
            "Press CTRL+C to stop."
        )

        print("")


        while True:

            time.sleep(1)


    except KeyboardInterrupt:

        print(
            "\nStopping Tommy..."
        )


    finally:

        if backend:

            backend.terminate()

            backend.wait()


if __name__ == "__main__":

    main()