
from app.services.ingestion.github_ingestion import (
    ingest_github_repository,
)


if __name__ == "__main__":
    result = ingest_github_repository(
        "https://github.com/PriyankaR1712/RepoLens-AI"
    )

    print("\n========== INGESTION RESULT ==========")

    for key, value in result.items():
        if key == "files":
            print(f"{key}: {len(value)} files")
        else:
            print(f"{key}: {value}")

    print("======================================")
