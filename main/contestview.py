from flask import render_template, session, flash, redirect
import awstools
import contestmode
from datetime import datetime, timedelta
from forms import beginContestForm

def contest(contestId):
    contestinfo = awstools.getContestInfo(contestId)

    if contestinfo == None:
        return "sorry this page doesn't exist"

    if contestmode.contest() and contestmode.contestId() != contestId:
        flash('Sorry, this is the only contest you can view in contest mode now', 'warning')
        return redirect(f'/contest/{contestmode.contestId()}')

    problemNames = contestinfo['problems']
    problems = []

    for P in problemNames:
        t = awstools.getProblemInfo(P)
        if type(t) != str:
            problems.append(t)

    if contestId == 'analysismirror':
        problems = awstools.getAllProblemsLimited()
        problems = [P for P in problems if P['analysisVisible']]
    
    userInfo = awstools.getCurrentUserInfo()
    if userInfo == None:
        flash("Please login to view this page!", "warning")
        
        if contestmode.contest():
            return redirect('/announcements')

        return redirect("/")
		
    username = userInfo["username"]
    
    # not userInfo["username"] in contestinfo.users
    if contestinfo["public"] == 0 and not username in contestinfo["users"] and userInfo['role'] != 'superadmin' and username not in contestmode.allowedusers():
        flash("Sorry, you've not been invited to this private contest!", "warning")
        return redirect("/announcements")
    
    showScoreboard = True
    if not contestinfo["publicScoreboard"] and (userInfo['role'] != "admin" and userInfo['role'] != "superadmin"):
        showScoreboard = False

    start = datetime.strptime(contestinfo['startTime'], "%Y-%m-%d %X") 
    now = datetime.now() + timedelta(hours = 8)

    past = False
    endTime = contestinfo['endTime']
    if endTime != "Unlimited":
        end = datetime.strptime(endTime, "%Y-%m-%d %X")
        past = (end < now)

    if not past and (not contestmode.contest() or (userInfo['role'] != 'superadmin' and username not in contestmode.allowedusers())) and ((contestinfo["public"] and not username in contestinfo["users"]) or contestinfo["users"][username] == "0") :
        form = beginContestForm()
        startTime = start
        if now >= start:
            startTime -= timedelta(hours = 100)
        startTime = startTime.strftime("%b %-d, %Y, %X")

        if form.is_submitted():
            if now < start:
                flash("Sorry, this contest hasn't started yet", "warning")
                return redirect(f"/announcements")
            if userInfo['role'] == 'disabled' or userInfo['role'] == 'locked':
                flash("Your account is unfortunately disabled. If you just registered, please wait for an admin to enable your account.", "warning")
                return redirect(f"/announcements")
                
            awstools.addParticipation(contestId, username)
            return redirect(f"/contest/{contestId}")

        return render_template("begincontest.html", contest=contestmode.contest(), userinfo=userInfo, contestinfo=contestinfo, form=form, startTime=startTime, users=contestmode.allowedusers(), cppref=contestmode.cppref())

    if username in contestinfo["scores"]:
        problemScores = contestinfo["scores"][username]
    elif not past:
        problemScores = userInfo['problemScores']
    else:
        problemScores = {}
    problemInfo = [dict((key,value) for key, value in P.items() if key in ['problemName','analysisVisible','title', 'source', 'author','problem_type','noACs','contestLink','EE']) for P in problems] #impt info goes into the list (key in [list])
    
    for problem in problemInfo:
        if problem['analysisVisible'] == False and userInfo['role'] == 'member':
            problem['analysisVisible'] = True
            awstools.makeAnalysisVisible(problem["problemName"])
    
     
    totalScore = 0
    maxScore = len(problemInfo) * 100
    for i in range(len(problemInfo)):
        name = problemInfo[i]['problemName']
        score = "N/A" 
        if name in problemScores:
            score = problemScores[name]
            totalScore += score
        problemInfo[i]['yourScore'] = score
        author = problemInfo[i]['author']
        problemInfo[i]['author'] = [x.replace(" ","") for x in author.split(",")]

    if maxScore != 0:
        percent = 100 * (totalScore / maxScore)
    else:
        percent = 100
    
    endTimeStr = contestinfo["endTime"]
    duration = contestinfo['duration']
    startTime = datetime.strptime(contestinfo["startTime"], "%Y-%m-%d %X")
    contestantStartTime = None
    if username in contestinfo["users"]:
        if contestinfo["users"][username] != "0":
            contestantStartTime = datetime.strptime(contestinfo["users"][username], "%Y-%m-%d %X")
    if endTimeStr == "Unlimited" and duration == 0:
        endTime = None
    else:
        if endTimeStr == "Unlimited":
            if contestantStartTime != None:
                endTime = contestantStartTime + timedelta(minutes = int(duration))
            else:
                endTime = None
        else:
            endTime = datetime.strptime(endTimeStr, "%Y-%m-%d %X") - timedelta(hours = 8)#based on official end Time
            duration = contestinfo['duration']
            if duration != 0:
                if contestantStartTime != None:
                    endTime = min(endTime, contestantStartTime + timedelta(minutes = int(duration)))
        
        #convert to strin
        if endTime != None:
            endTime += timedelta(hours = 8)
            endTime = endTime.strftime("%b %-d, %Y, %X")

    return render_template('contest.html', problemInfo=problemInfo, showScoreboard = showScoreboard, contestinfo = contestinfo, totalScore = totalScore, maxScore = maxScore, percent = percent, contest=contestmode.contest(), endTime=endTime, userinfo=userInfo, users=contestmode.allowedusers(), cppref=contestmode.cppref(), socket=contestmode.socket())
