from bokeh.io import show
from bokeh.models import ColumnDataSource, DataTable, TableColumn
from bokeh.layouts import column
import json
import random

try:
    with open("fetched_data.json", "r") as f:
        fetched_data = json.load(f)
    print(f"Loaded data for {len(fetched_data)} teams")

    rows = []
    for team_num, matches in fetched_data.items():
        for match_id, match_data in matches.items():
            row = {"team": team_num, "match": match_id}

            for field_name, field_value in match_data.items():
                if isinstance(field_value, dict):
                    if "integerValue" in field_value:
                        row[field_name] = int(field_value["integerValue"])
                    elif "stringValue" in field_value:
                        row[field_name] = field_value["stringValue"]
                    elif "doubleValue" in field_value:
                        row[field_name] = float(field_value["doubleValue"])
                    elif "booleanValue" in field_value:
                        row[field_name] = field_value["booleanValue"]
                    elif "mapValue" in field_value and field_name == "robotError":
                        map_fields = field_value["mapValue"].get("fields", {})
                        true_errors = []
                        for error_name, error_data in map_fields.items():
                            if (
                                isinstance(error_data, dict)
                                and "booleanValue" in error_data
                            ):
                                if error_data["booleanValue"] is True:
                                    true_errors.append(error_name)
                        row[field_name] = ", ".join(true_errors) if true_errors else ""
                    else:
                        row[field_name] = str(field_value)
                else:
                    row[field_name] = field_value

            rows.append(row)

    if rows:
        all_columns = set()
        for row in rows:
            all_columns.update(row.keys())
        all_columns = sorted(list(all_columns))

        data = {col: [] for col in all_columns}
        for row in rows:
            for col in all_columns:
                data[col].append(row.get(col, ""))

        print(f"Created table with {len(rows)} rows and {len(all_columns)} columns")
        print(f"Columns: {all_columns}")
    else:
        print("No data found in fetched_data.json")
        data = dict(
            phases=[
                "auto",
                "transition",
                "teleop",
                "phase1",
                "phase2",
                "phase3",
                "phase4",
            ],
            scores=[random.randint(0, 100) for i in range(7)],
        )

except FileNotFoundError:
    print("fetched_data.json not found. Using random data.")
    data = dict(
        phases=["auto", "transition", "teleop", "phase1", "phase2", "phase3", "phase4"],
        scores=[random.randint(0, 100) for i in range(7)],
    )
except json.JSONDecodeError:
    print("Error parsing fetched_data.json. Using random data.")
    data = dict(
        phases=["auto", "transition", "teleop", "phase1", "phase2", "phase3", "phase4"],
        scores=[random.randint(0, 100) for i in range(7)],
    )


source = ColumnDataSource(data)

columns = [TableColumn(field=col, title=col) for col in data.keys()]

num_rows = len(next(iter(data.values()))) if data else 7
num_cols = len(data.keys())

calculated_height = max(400, min(num_rows * 30 + 50, 800))

calculated_width = max(1200, num_cols * 120)

table = DataTable(
    source=source,
    columns=columns,
    width=calculated_width,
    height=calculated_height,
    index_position=0,  
    sortable=True, 
    selectable=True,
)

layout = column(table)

show(layout)
