import json
import fetchfromdb
from bokeh.io import show
from bokeh.models import ColumnDataSource, DataTable, TableColumn, HTMLTemplateFormatter
from bokeh.layouts import column

fetchfromdb.fetch()
COLUMN_ORDER = [
    "eventName",
    "team",
    "match",
    "name",
    "scoutingTeam",
    "teamNumber",
    "matchNumber",
    "autoFuel",
    "autoUnderTrench",
    "autoClimbed",
    "transitionFuel",
    "shift1HubActive",
    "shift1Fuel",
    "shift1Defense",
    "shift2HubActive",
    "shift2Fuel",
    "shift2Defense",
    "shift3HubActive",
    "shift3Fuel",
    "shift3Defense",
    "shift4HubActive",
    "shift4Fuel",
    "shift4Defense",
    "endgameFuel",
    "endgameClimbLevel",
    "crossedBump",
    "underTrench",
    "robotError",
    "notes",
]

NUMERIC_GRADIENT_COLUMNS = [
    "transitionFuel",
    "shift1Fuel",
    "shift2Fuel",
    "shift3Fuel",
    "shift4Fuel",
    "autoFuel",
    "endgameFuel",
]


def loadAndFlattenData(filePath):
    try:
        with open(filePath, "r") as f:
            fullData = json.load(f)

        rootData = fullData.get("root", {})
        print(f"Loaded data for {len(rootData)} teams")

        rows = []
        for teamNum, matches in rootData.items():
            for matchId, matchFields in matches.items():
                row = {"team": teamNum, "match": matchId}

                # Iterate fields
                for key, value in matchFields.items():
                    if key == "robotError" and isinstance(value, dict):
                        trueErrors = [k for k, v in value.items() if v is True]
                        row[key] = ", ".join(trueErrors)
                    else:
                        row[key] = value
                rows.append(row)
        return rows
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return []


allRows = loadAndFlattenData("fetched_data.json")

if allRows:
    allKeys = set().union(*(row.keys() for row in allRows))
    orderedCols = [c for c in COLUMN_ORDER if c in allKeys]
    otherCols = sorted(list(allKeys - set(COLUMN_ORDER)))
    finalColumns = orderedCols + otherCols

    plotData = {col: [row.get(col, "") for row in allRows] for col in finalColumns}

    for col in NUMERIC_GRADIENT_COLUMNS:
        if col in plotData:
            vals = [float(v) if v not in ["", None] else 0 for v in plotData[col]]
            maxV = max(vals) if vals and max(vals) > 0 else 1

            colors = []
            for v in vals:
                ratio = min(max(v / maxV, 0), 1)
                r = int(255 - (75 * ratio))
                g = int(180 + (75 * ratio))
                colors.append(f"rgb({r}, {g}, 180)")
            plotData[f"{col}Color"] = colors

    # 4. Logic for Booleans
    for col in finalColumns:
        if col not in NUMERIC_GRADIENT_COLUMNS:
            colors = []
            for val in plotData[col]:
                if val is True:
                    colors.append("#d4edda")  # Light Green
                elif val is False:
                    colors.append("#f8d7da")  # Light Red
                else:
                    colors.append("white")
            plotData[f"{col}Color"] = colors

    source = ColumnDataSource(plotData)

    tableColumns = []
    for col in finalColumns:
        formatter = HTMLTemplateFormatter(
            template=f"""
            <div style="background-color: <%= {col}Color %>; 
                        padding: 4px; margin: -4px; height: 100%;">
                <%= value %>
            </div>
        """
        )

        colWidth = 250 if col in ["notes", "robotError", "eventName"] else 100
        tableColumns.append(
            TableColumn(field=col, title=col, formatter=formatter, width=colWidth)
        )

    numRows = len(allRows)
    numCols = len(finalColumns)

    dynamicHeight = 1200 if numRows > 40 else max(400, min(numRows * 30 + 50, 800))
    dynamicWidth = max(1200, numCols * 100)

    # 7. Create Layout
    dataTable = DataTable(
        source=source,
        columns=tableColumns,
        width=dynamicWidth,
        height=dynamicHeight,
        sortable=True,
        editable=False,
        index_position=0,
    )

    show(column(dataTable))
else:
    print("No data to display.")
