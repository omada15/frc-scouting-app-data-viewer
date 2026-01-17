import requests
import json

# Load credentials from serviceAccountKey.json
try:
    with open("serviceAccountKey.json", "r") as f:
        config = json.load(f)
    API_KEY = config.get("apiKey")
    PROJECT_ID = config.get("projectId")
    print("Credentials loaded successfully from serviceAccountKey.json")
except FileNotFoundError:
    print("Error: Service account key file not found.")
    print("Please ensure serviceAccountKey.json exists in the current directory.")
    exit()
except json.JSONDecodeError:
    print("Error: Invalid JSON in serviceAccountKey.json")
    exit()


def fetch_data_by_teamnum(teamnum, all_data=None):
    """
    Recursively fetch all data for a specific team number.
    Traverses {teamnum}/{match}/... structure
    """
    if all_data is None:
        all_data = {}

    path = f"{teamnum}"
    print(f"\n--- Fetching team: '{teamnum}' ---")
    try:
        url = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/{path}"
        print(f"URL: {url}")
        params = {"key": API_KEY, "pageSize": "1000"}

        response = requests.get(url, params=params)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()

            if "documents" in result and result["documents"]:
                print(f"Found {len(result['documents'])} matches for team {teamnum}")
                all_data[teamnum] = {}

                for doc in result["documents"]:
                    doc_name = doc["name"].split("/")[
                        -1
                    ]

                    if "fields" in doc and doc["fields"]:
                        all_data[teamnum][doc_name] = doc["fields"]

                return all_data
            else:
                print(f"No matches found for team {teamnum}")
                return all_data
        else:
            print(
                f"Error {response.status_code} fetching team {teamnum}: {response.text}"
            )
            return all_data

    except Exception as e:
        print(f"Error fetching team {teamnum}: {e}")
        import traceback

        traceback.print_exc()
        return all_data


def fetch_all_data_recursive(path="", all_data=None):
    """
    Recursively fetch all data from nested collections.
    Assumes structure: {teamnum}/{match}/...
    """
    if all_data is None:
        all_data = {}

    print(f"\n--- Fetching from path: '{path}' ---")
    try:
        url = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents{path}"
        print(f"URL: {url}")
        params = {"key": API_KEY, "pageSize": "1000"}

        response = requests.get(url, params=params)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()

            if "documents" in result and result["documents"]:
                print(f"Found {len(result['documents'])} items at {path}")

                for doc in result["documents"]:
                    doc_name = doc["name"].split("/")[-1]  # Get just the document ID
                    doc_path = f"{path}/{doc_name}"

                    # Check if this is a document with data or if it has subcollections
                    if "fields" in doc and doc["fields"]:
                        # This is a document with data
                        all_data[doc_path] = doc["fields"]
                        print(f"  Stored: {doc_path}")
                    else:
                        # This might be a document with subcollections, try to fetch them
                        print(f"  Checking subcollections of {doc_path}...")
                        fetch_all_data_recursive(doc_path, all_data)

                return all_data
            else:
                print(f"No documents found at {path}")
                return all_data
        else:
            print(f"Error {response.status_code}: {response.text}")
            return all_data

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return all_data
        return None


if __name__ == "__main__":
    team_numbers = ["1000"]

    all_data = {}

    for teamnum in team_numbers:
        fetch_data_by_teamnum(teamnum, all_data)

    if all_data:
        for teamnum, matches in all_data.items():
            print(f"Team {teamnum}: {len(matches)} matches")

        print(json.dumps(all_data, indent=4))

        output_filename = "fetched_data.json"
        try:
            with open(output_filename, "w") as outfile:
                json.dump(all_data, outfile, indent=4)
        except Exception as e:
            print(f"Error writing to file: {e}")
    else:
        print("\nNo data found. Check if the team numbers are correct.")
