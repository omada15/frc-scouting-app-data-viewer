import json
import statistics
import logger as l

l.clear()
def getTeamMatches(dataRoot, teamNum):
    strTeam = str(teamNum)
    if strTeam not in dataRoot:
        print(f"Team {teamNum} not found in data.")
        return []


    teamDict = dataRoot[strTeam]
    return list(teamDict.values())



def autoCalc(allTeams):
    l.log(allTeams)

    def getTeamProfile(teamObj):
        historyPoints = []
        climbAttempts = 0
        totalMatches = 0

        matches = teamObj.get("matches", [])

        for match in matches:
            err = match.get("robotError", {})
            # if err.get("Did not participate", False):
            #    continue

            totalMatches += 1

            fuel = match.get("autoFuel", 0)
            climbed = match.get("autoClimbed", False)
            climbPoints = 15 if climbed else 0

            if climbed:
                climbAttempts += 1
            historyPoints.append(fuel + climbPoints)
        l.log(historyPoints)
        if not historyPoints:
            return {
                "id": teamObj["teamNumber"],
                "reliability": 0.0,
                "climbFreq": 0.0,
                "floorTotal": 0,
                "likelyFuel": 0,
                "ceilingFuel": 0,
            }

        maxScore = max(historyPoints)
        successThreshold = maxScore * 0.5
        passFuelScores = []
        failSetScores = []
        passSetScores = []

        for i, score in enumerate(historyPoints):
            matchErr = matches[i].get("robotError", {})
            isAutoStop = matchErr.get("Auto stop", False)

            if score < successThreshold or False:
                failSetScores.append(score)
            else:
                passSetScores.append(score)
                passFuelScores.append(matches[i].get("autoFuel", 0))

        reliability = len(passSetScores) / len(historyPoints) if historyPoints else 0

        likelyFuel = statistics.median(passFuelScores) if passFuelScores else 0
        ceilingFuel = max(passFuelScores) if passFuelScores else 0
        floorTotal = (
            statistics.mean(failSetScores) if failSetScores else (maxScore * 0.2)
        )

        return {
            "id": teamObj["teamNumber"],
            "reliability": reliability,
            "climbFreq": climbAttempts / totalMatches if totalMatches > 0 else 0,
            "floorTotal": floorTotal,
            "likelyFuel": likelyFuel,
            "ceilingFuel": ceilingFuel,
        }

    teamProfiles = [getTeamProfile(t) for t in allTeams]
    redProfiles = teamProfiles[0:3]
    blueProfiles = teamProfiles[3:6]

    def calculateAllianceStats(profiles):
        potentialClimbers = [p for p in profiles if p["climbFreq"] > 0.40]
        potentialClimbers.sort(key=lambda x: x["reliability"], reverse=True)
        allowedClimbers = [p["id"] for p in potentialClimbers[:2]]

        totalLikely = 0

        for bot in profiles:
            climbPoints = 15 if bot["id"] in allowedClimbers else 0
            totalLikely += bot["likelyFuel"] + climbPoints

        return {"likely": totalLikely, "profileData": profiles}

    redStats = calculateAllianceStats(redProfiles)
    blueStats = calculateAllianceStats(blueProfiles)

    winner = "Red" if redStats["likely"] > blueStats["likely"] else "Blue"
    if redStats["likely"] == blueStats["likely"]:
        winner = "Tie"

    return {
        "redScore": redStats["likely"],
        "blueScore": blueStats["likely"],
        "predictedAutoWinner": winner,
    }

def teleopCalc(allTeams, autoWinner):

    TRANSITION_TIME = 10
    SHIFT_TIME = 25
    ENDGAME_TIME = 30
    ALLIANCE_HOPPER_CAP = 24

    def getTeleopProfile(teamObj):
        matches = teamObj.get("matches", [])
        totalActiveSecs = 0
        totalFuel = 0
        endgamePoints = []

        fatalErrors = []#"Emergency Stop", "Robot Unresponsive", "Robot unresponsive"]

        for match in matches:
            err = match.get("robotError", {})
            if any(err.get(k, False) for k in fatalErrors): #or err.get("Did not participate", False):
                continue

            activeSecs = TRANSITION_TIME + ENDGAME_TIME
            matchFuel = match.get("transitionFuel", 0) + match.get("endgameFuel", 0)

            for i in range(1, 5):
                if match.get(f"shift{i}HubActive", False):
                    activeSecs += SHIFT_TIME
                    matchFuel += match.get(f"shift{i}Fuel", 0)

            totalActiveSecs += activeSecs
            totalFuel += matchFuel

            climbStr = str(match.get("endgameClimbLevel", "0"))
            pts = 0
            if climbStr == "1":
                pts = 10
            elif climbStr == "2":
                pts = 20
            elif climbStr == "3":
                pts = 30
            endgamePoints.append(pts)

        if totalActiveSecs == 0:
            return {"fuelRate": 0.0, "endgame": 0.0}

        return {
            "fuelRate": totalFuel / totalActiveSecs, 
            "endgame": statistics.mean(endgamePoints) if endgamePoints else 0,
        }

    teamProfiles = [getTeleopProfile(t) for t in allTeams]
    redProfiles = teamProfiles[0:3]
    blueProfiles = teamProfiles[3:6]


    if autoWinner == "Red":
        redSchedule = [False, True, False, True]
        blueSchedule = [True, False, True, False]
    elif autoWinner == "Blue":
        redSchedule = [True, False, True, False]
        blueSchedule = [False, True, False, True]
    else:
        print("tie auto ")
        redSchedule = [True, True, True, True]
        blueSchedule = [True, True, True, True]

    def simulateGame(profiles, schedule):
        rawAllianceRate = sum(p["fuelRate"] for p in profiles)

        adjRate = rawAllianceRate * 0.90

        score = 0
        hopper = 0  

        score += adjRate * TRANSITION_TIME

        for isActive in schedule:
            if autoWinner == "Tie":
                score += adjRate * SHIFT_TIME
            elif isActive:
                score += (adjRate * SHIFT_TIME) + hopper
                hopper = 0
            else:
                hopper += adjRate * SHIFT_TIME
                if hopper > ALLIANCE_HOPPER_CAP:
                    hopper = ALLIANCE_HOPPER_CAP

        score += (
            adjRate * (ENDGAME_TIME / 2)
        ) + hopper

        climbScore = sum(p["endgame"] for p in profiles)

        return round(score + climbScore, 1)

    redTeleop = simulateGame(redProfiles, redSchedule)
    blueTeleop = simulateGame(blueProfiles, blueSchedule)

    return {"redTeleop": redTeleop, "blueTeleop": blueTeleop}

def predictMatch(jsonData, redTeamNums, blueTeamNums):
    """
    Main entry point.
    1. Loads team data.
    2. Runs Auto Calc.
    3. Runs Teleop Calc.
    4. Returns Final Prediction Dictionary.
    """

    allTeamsList = []

    for tNum in redTeamNums + blueTeamNums:
        tObj = {
            "teamNumber": tNum,
            "matches": getTeamMatches(jsonData.get("root", {}), tNum),
        }
        allTeamsList.append(tObj)

    autoResult = autoCalc(allTeamsList)

    teleopResult = teleopCalc(allTeamsList, autoResult["predictedAutoWinner"])

    l.log(tObj)
    finalPrediction = {
        "redAlliance": {
            "teams": redTeamNums,
            "autoLikely": autoResult["redScore"],
            "teleopLikely": teleopResult["redTeleop"],
            "totalScore": round(autoResult["redScore"] + teleopResult["redTeleop"]),
        },
        "blueAlliance": {
            "teams": blueTeamNums,
            "autoLikely": autoResult["blueScore"],
            "teleopLikely": teleopResult["blueTeleop"],
            "totalScore": round(autoResult["blueScore"] + teleopResult["blueTeleop"]),
        },
        "simulationDetails": {
            "autoWinner": autoResult["predictedAutoWinner"],
            "note": "Teleop prediction adjusted for Active/Inactive hub schedule.",
        },
    }

    return finalPrediction

if __name__ == "__main__":

    data = json.load(open("fetched_data.json"))

    results = predictMatch(data, [9998, 9997, 9996], [9995, 9994, 9993])

    with open("teamPredictor.json", "w") as f:
        json.dump(results, f, indent=4)

    l.log("Currently, we are not accounting for autostop and did not participate. please modify before use. FatalErrors also does not exist")
