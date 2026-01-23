import json
import fetchfromdb
from bokeh.io import output_file, show
from bokeh.models import ColumnDataSource, DataTable, TableColumn, HTMLTemplateFormatter

fetchfromdb.fetch()

# Configuration
COLUMN_ORDER = [
    "teamNumber",
    "entries",
    "avgAutoFuel",
    "avgTransitionFuel",
    "avgFirstActiveHubFuel",
    "avgSecondActiveHubFuel",
    "avgEndgameFuel",
    "avgTotalFuel",
]

# List of all variables to receive gradients
GRADIENT_COLUMNS = [
    "avgAutoFuel",
    "avgTransitionFuel",
    "avgFirstActiveHubFuel",
    "avgSecondActiveHubFuel",
    "avgEndgameFuel",
    "avgTotalFuel",
]


def calculateAverage(lst):
    return round(sum(lst) / len(lst), 2) if lst else 0


def processTeamAverages(filePath):
    try:
        with open(filePath, "r") as f:
            fetchedData = json.load(f)

        teamList = fetchedData.get("team", [])
        rootData = fetchedData.get("root", {})
        print(f"Loaded data for {len(rootData)} teams")

        summaryData = {
            "teamNumber": [],
            "entries": [],
            "avgAutoFuel": [],
            "avgTransitionFuel": [],
            "avgFirstActiveHubFuel": [],
            "avgSecondActiveHubFuel": [],
            "avgEndgameFuel": [],
            "avgTotalFuel": [],
        }

        for team in teamList:
            teamMatches = rootData.get(str(team), {})
            matchCount = len(teamMatches)

            tempAuto, tempTransition, tempFirstHub = [], [], []
            tempSecondHub, tempEndgame, tempTotal = [], [], []

            for matchId, matchData in teamMatches.items():
                auto = matchData.get("autoFuel", 0)
                transition = matchData.get("transitionFuel", 0)
                endgame = matchData.get("endgameFuel", 0)

                firstShift = 1 if matchData.get("shift1HubActive") else 2
                secondShift = 3 if matchData.get("shift3HubActive") else 4

                firstHub = matchData.get(f"shift{firstShift}Fuel", 0)
                secondHub = matchData.get(f"shift{secondShift}Fuel", 0)

                total = auto + transition + endgame + firstHub + secondHub

                tempAuto.append(auto)
                tempTransition.append(transition)
                tempFirstHub.append(firstHub)
                tempSecondHub.append(secondHub)
                tempEndgame.append(endgame)
                tempTotal.append(total)

            summaryData["teamNumber"].append(team)
            summaryData["entries"].append(matchCount)
            summaryData["avgAutoFuel"].append(calculateAverage(tempAuto))
            summaryData["avgTransitionFuel"].append(calculateAverage(tempTransition))
            summaryData["avgFirstActiveHubFuel"].append(calculateAverage(tempFirstHub))
            summaryData["avgSecondActiveHubFuel"].append(
                calculateAverage(tempSecondHub)
            )
            summaryData["avgEndgameFuel"].append(calculateAverage(tempEndgame))
            summaryData["avgTotalFuel"].append(calculateAverage(tempTotal))

        return summaryData

    except Exception as e:
        print(f"Error: {e}")
        return None


# --- Main Execution ---
processedSummary = processTeamAverages("fetched_data.json")

if processedSummary:
    output_file("team_averages.html")

    # 1. Apply Gradient Logic
    for col in GRADIENT_COLUMNS:
        if col in processedSummary:
            vals = [float(v) for v in processedSummary[col]]
            maxV = max(vals) if vals and max(vals) > 0 else 1

            colors = []
            for v in vals:
                ratio = min(max(v / maxV, 0), 1)
                # Red (255, 180, 180) to Green (180, 255, 180)
                r = int(255 - (75 * ratio))
                g = int(180 + (75 * ratio))
                colors.append(f"rgb({r}, {g}, 180)")
            processedSummary[f"{col}Color"] = colors

    source = ColumnDataSource(processedSummary)

    # 2. Build Columns with Formatters
    tableColumns = []
    for col in COLUMN_ORDER:
        title = col.replace("avg", "Avg ").replace("Fuel", " Fuel")

        # Check if this column needs a gradient
        if col in GRADIENT_COLUMNS:
            formatter = HTMLTemplateFormatter(
                template=f"""
                <div style="background-color: <%= {col}Color %>; 
                            padding: 4px; margin: -4px; height: 100%;">
                    <%= value %>
                </div>
            """
            )
            tableColumns.append(
                TableColumn(field=col, title=title, formatter=formatter, width=120)
            )
        else:
            tableColumns.append(TableColumn(field=col, title=title, width=100))

    # 3. Dynamic Sizing
    numTeams = len(processedSummary["teamNumber"])
    dynamicHeight = max(400, min(numTeams * 30 + 50, 800))
    dynamicWidth = max(1000, len(tableColumns) * 125)

    dataTable = DataTable(
        source=source,
        columns=tableColumns,
        width=dynamicWidth,
        height=dynamicHeight,
        selectable=True,
        sortable=True,
        index_position=None,
    )

    show(dataTable)
