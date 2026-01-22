from app.worker import Worker


def main():
    worker = Worker()
    worker.run()


if __name__ == "__main__":
    main()
