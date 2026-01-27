import json
import statistics
import math
import logger as l

# Helper functions and probability calculations for match outcome predictions

l.clear()
def getTeamMatches(dataRoot, teamNum):
    """Parses your specific nested JSON structure."""
    strTeam = str(teamNum)
    if strTeam not in dataRoot:
        return []
    # Convert map of matches into a list of matches
    return list(dataRoot[strTeam].values())


def calculateWinChance(redStats, blueStats):
    # Uses Normal Distribution (Mean=Likely, Sigma=(Range/6)) to find
    # probability of Red Score > Blue Score.
    muRed = redStats["likely"]
    muBlue = blueStats["likely"]

    # Calculate Sigma based on 6-Sigma spread (99.7% confidence interval)
    rangeRed = redStats["max"] - redStats["min"]
    rangeBlue = blueStats["max"] - blueStats["min"]

    # Epsilon to prevent zero div error
    sigmaRed = rangeRed / 6 if rangeRed > 1 else 1.0
    sigmaBlue = rangeBlue / 6 if rangeBlue > 1 else 1.0

    muDiff = muRed - muBlue
    sigmaDiff = math.sqrt(sigmaRed**2 + sigmaBlue**2)

    # Z-score where value is 0 (Tie)
    zScore = (0 - muDiff) / sigmaDiff

    # Calculate Probability
    probBlueWins = 0.5 * (1 + math.erf(zScore / math.sqrt(2)))
    probRedWins = 1.0 - probBlueWins

    return {
        "redWinPct": round(probRedWins * 100, 1),
        "blueWinPct": round(probBlueWins * 100, 1),
    }


# 3. Auto algo


def autoCalc(allTeams):
    def getTeamProfile(teamObj):
        historyPoints = []
        climbAttempts = 0
        totalMatches = 0
        matches = teamObj.get("matches", [])

        for match in matches:
            if match.get("robotError", {}).get("Did not participate", False):
                continue
            totalMatches += 1

            # Fuel = 1, Level 1 Climb = 15 (if successful)
            points = match.get("autoFuel", 0)
            climbed = match.get("autoClimbed", False)
            if climbed:
                points += 15
                climbAttempts += 1

            historyPoints.append(points)

        if not historyPoints:
            return {
                "id": teamObj["teamNumber"],
                "reliability": 0.0,
                "climbFreq": 0.0,
                "floorTotal": 0,
                "likelyTotal": 0,
                "ceilingTotal": 0,
                "maxScore": 0,
            }

        maxScore = max(historyPoints)
        successThreshold = maxScore * 0.5
        passSet = []
        failSet = []

        for i, score in enumerate(historyPoints):
            # Check mixed case keying
            err = matches[i].get("robotError", {})
            isAutoStop = err.get("Auto Stop", False) or err.get("Auto stop", False)

            # If Auto Stop occurred OR score was tragically low
            if score < successThreshold or isAutoStop:
                failSet.append(score)
            else:
                passSet.append(score)

        reliability = len(passSet) / len(historyPoints)

        # Floor = Average of failures. If no failures recorded, Floor = Likely * 0.8
        # Likely = Median of Successes.
        # Ceiling = Max of Successes.
        if passSet:
            likelyTotal = statistics.median(passSet)
            ceilingTotal = max(passSet)
        else:
            likelyTotal = 0
            ceilingTotal = 0

        floorTotal = statistics.mean(failSet) if failSet else (likelyTotal * 0.8)

        return {
            "id": teamObj["teamNumber"],
            "reliability": reliability,
            "climbFreq": climbAttempts / totalMatches if totalMatches else 0,
            "floorTotal": floorTotal,
            "likelyTotal": likelyTotal,  # Note: Includes climb points initially
            "ceilingTotal": ceilingTotal,
        }

    profiles = [getTeamProfile(t) for t in allTeams]

    def calculateAlliance(allianceProfiles):
        # 3v3 Constraint: Only 2 Climbs allowed
        potentialClimbers = [p for p in allianceProfiles if p["climbFreq"] > 0.40]
        potentialClimbers.sort(key=lambda x: x["reliability"], reverse=True)
        allowedClimberIds = [p["id"] for p in potentialClimbers[:2]]

        totalFloor = 0
        totalLikely = 0
        totalCeiling = 0

        for bot in allianceProfiles:
            # We strip 15 points if they are a climber but NOT allowed due to rules
            isClimber = bot["climbFreq"] > 0.40  # Simple heuristic check
            pointsToRemove = (
                15 if (isClimber and bot["id"] not in allowedClimberIds) else 0
            )

            # Prevent negative scores
            totalFloor += max(0, bot["floorTotal"] - pointsToRemove)
            totalLikely += max(0, bot["likelyTotal"] - pointsToRemove)
            totalCeiling += max(0, bot["ceilingTotal"] - pointsToRemove)

        return {
            "min": round(totalFloor, 1),
            "likely": round(totalLikely, 1),
            "max": round(totalCeiling, 1),
        }

    redStats = calculateAlliance(profiles[0:3])
    blueStats = calculateAlliance(profiles[3:6])

    winner = "Red" if redStats["likely"] > blueStats["likely"] else "Blue"
    if redStats["likely"] == blueStats["likely"]:
        winner = "Tie"

    return {"red": redStats, "blue": blueStats, "winner": winner}


# teleop algo

def teleopCalc(allTeams, autoWinner, defenseFactored=False):
    # Constants
    TRANSITION_TIME = 10
    SHIFT_TIME = 25
    ENDGAME_TIME = 30
    ALLIANCE_CAP = 24

    def getProfile(teamData):
        validMatches = 0
        fuelRates = []  # List of avg fuel/sec per match
        endgamePts = []
        defenseCount = 0

        matches = teamData.get("matches", [])

        for match in matches:
            err = match.get("robotError", {})
            # Filter fatal errors (data sanitization)
            if any(
                err.get(k, False)
                for k in ["Emergency Stop", "Robot Unresponsive", "Robot unresponsive"]
            ):
                continue
            if err.get("Did not participate", False):
                continue

            validMatches += 1

            # Check Defense (boolean check in shifts)
            if any(match.get(f"shift{i}Defense", False) for i in range(1, 5)):
                defenseCount += 1 if defenseFactored else 0

            # Calc Rate: Fuel Scored / Seconds Hub was Active for that specific match
            activeSecs = TRANSITION_TIME + ENDGAME_TIME
            matchFuel = match.get("transitionFuel", 0) + match.get("endgameFuel", 0)

            for i in range(1, 5):
                if match.get(f"shift{i}HubActive", False):
                    activeSecs += SHIFT_TIME
                    matchFuel += match.get(f"shift{i}Fuel", 0)

            if activeSecs > 0:
                fuelRates.append(matchFuel / activeSecs)

            # Endgame
            lvl = str(match.get("endgameClimbLevel", "0"))
            pts = 0
            if lvl == "1":
                pts = 10
            elif lvl == "2":
                pts = 20
            elif lvl == "3":
                pts = 30
            endgamePts.append(pts)

        if not fuelRates:
            return {
                "minR": 0,
                "likelyR": 0,
                "maxR": 0,
                "endMin": 0,
                "endLikely": 0,
                "endMax": 0,
                "defRating": 0,
            }

        fuelRates.sort()
        return {
            "minR": fuelRates[0],
            "likelyR": statistics.median(fuelRates),
            "maxR": fuelRates[-1],  # Max observed throughput
            "endMin": 0,  # Assume fall
            "endLikely": statistics.mean(endgamePts) if endgamePts else 0,
            "endMax": max(endgamePts) if endgamePts else 0,
            "defRating": defenseCount / validMatches,
        }

    profiles = [getProfile(t) for t in allTeams]
    l.log(profiles)
    redProfs = profiles[0:3]
    blueProfs = profiles[3:6]

    # Set Schedules based on Auto
    if autoWinner == "Red":
        redSched, blueSched = [False, True, False, True], [True, False, True, False]
    elif autoWinner == "Blue":
        redSched, blueSched = [True, False, True, False], [False, True, False, True]
    else:
        redSched, blueSched = [True, True, True, True], [
            True,
            True,
            True,
            True,
        ]  # Average out tie

    # Calculate Alliance Pressure (how much they hurt opponents)
    redPress = min(
        sum(p["defRating"] for p in redProfs) * 0.15, 0.40
    )  # Cap 40% reduction
    bluePress = min(sum(p["defRating"] for p in blueProfs) * 0.15, 0.40)

    def runSim(myProfs, mySched, oppSched, oppPress, mode):
        # Pick rate stats based on mode (min/likely/max)
        rateKey = f"{mode}R"
        endKey = f"end{mode.capitalize()}"

        # Determine congestion and defensive environment
        congestion = 0.90  # Standard traffic
        defenseMod = 0.0

        if mode == "min":
            congestion = 0.80
            defenseMod = oppPress  # Full pressure applied
        elif mode == "max":
            congestion = 1.0  # Perfect coordination
            defenseMod = 0.0  # Opponents miss defense

        baseRate = sum(p[rateKey] for p in myProfs) * congestion

        score = 0
        hopper = 0

        # 1. Transition
        score += baseRate * TRANSITION_TIME

        # 2. Shifts
        for i in range(4):
            isActive = mySched[i]
            oppIsActive = oppSched[i]

            currentEfficiency = 1.0
            if isActive and not oppIsActive:
                currentEfficiency = 1.0 - defenseMod

            throughput = baseRate * currentEfficiency

            if autoWinner == "Tie":
                score += throughput * SHIFT_TIME
            elif isActive:
                score += (throughput * SHIFT_TIME) + hopper
                hopper = 0
            else:
                hopper += throughput * SHIFT_TIME
                if hopper > ALLIANCE_CAP:
                    hopper = ALLIANCE_CAP

        # 3. Endgame Scoring
        score += (baseRate * 15) + hopper  # 15s scoring / 15s climbing

        # 4. Endgame Climbs
        score += sum(p[endKey] for p in myProfs)

        return round(score, 1)

    return {
        "red": {
            "min": runSim(redProfs, redSched, blueSched, bluePress, "min"),
            "likely": runSim(redProfs, redSched, blueSched, bluePress, "likely"),
            "max": runSim(redProfs, redSched, blueSched, bluePress, "max"),
        },
        "blue": {
            "min": runSim(blueProfs, blueSched, redSched, redPress, "min"),
            "likely": runSim(blueProfs, blueSched, redSched, redPress, "likely"),
            "max": runSim(blueProfs, blueSched, redSched, redPress, "max"),
        },
        "schedWinner": autoWinner,
    }

def main():
    # 1. Parse JSON
    with open("fetched_data.json", "r") as inFile:
        rawJsonString = inFile.read()
    jsonData = json.loads(rawJsonString)

    # 2. Define Teams (Using IDs available in the data)
    redAlliance = [9998, 9997, 9996]
    blueAlliance = [9995, 9994, 9993]

    allTeamsList = []
    for tNum in redAlliance + blueAlliance:
        tObj = {
            "teamNumber": tNum,
            "matches": getTeamMatches(jsonData.get("root", {}), tNum),
        }
        allTeamsList.append(tObj)

    # 3. Predictions
    autoRes = autoCalc(allTeamsList)
    teleRes = teleopCalc(allTeamsList, autoRes["winner"])

    # 4. Sum Totals for Probability
    redFinal = {
        "min": round(autoRes["red"]["min"] + teleRes["red"]["min"], 1),
        "likely": round(autoRes["red"]["likely"] + teleRes["red"]["likely"], 1),
        "max": round(autoRes["red"]["max"] + teleRes["red"]["max"], 1),
    }

    blueFinal = {
        "min": round(autoRes["blue"]["min"] + teleRes["blue"]["min"], 1),
        "likely": round(autoRes["blue"]["likely"] + teleRes["blue"]["likely"], 1),
        "max": round(autoRes["blue"]["max"] + teleRes["blue"]["max"], 1),
    }

    winChances = calculateWinChance(redFinal, blueFinal)

    # 5. Pretty Print Output
    output = {
        "Red_Alliance": {
            "Teams": redAlliance,
            "Score_Prediction": redFinal,
            "Win_Chance": f"{winChances['redWinPct']}%",
        },
        "Blue_Alliance": {
            "Teams": blueAlliance,
            "Score_Prediction": blueFinal,
            "Win_Chance": f"{winChances['blueWinPct']}%",
        },
        "Simulation_Details": {
            "Auto_Winner": autoRes["winner"],
            "Schedule": f"{autoRes['winner']} controls cycle flow.",
        },
    }

    with open("teamPredictor.json", "w") as outFile:
        json.dump(output, outFile, indent=4)


if __name__ == "__main__":
    main()
