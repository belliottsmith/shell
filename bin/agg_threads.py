import re
import sys

assert sys.version_info >= (3,0)

re_trace = re.compile(
    "(java\\.lang\\.Thread\\.State: " +
    "|- parking to wait for  <[0-9a-fx]+>" +
    "|- waiting on <[0-9a-fx]+>" +
    "|- locked <[0-9a-fx]+>" +
    "|at " +
    "| - " +
    ").*")

re_state = re.compile("java\\.lang\\.Thread\\.State: ([A-Z_]+).*")
re_eclipse_thead = re.compile("Thread 0x[a-z0-9]+")
re_jdk8_thread = re.compile("\\s*Thread ([0-9xa-z]+): \\(state = ([A-Z_]+)\\)")
re_replace = re.compile("<[0-9a-fx]+>")
re_ignore_at_start = re.compile("[0-9]{4}(-[0-9]{2}){2} ([0-9]{2}:){2}[0-9]{2}" +
                                "|Full thread dump.*" +
                                "|")

def exit_with_usage(code=1):
    sys.stderr.write("Usage: {0} <file>\n".format(sys.argv[0]))
    sys.exit(code)

filename = sys.argv[1]
with open(filename) as f:
    stateToTraceToThread = {}
    currentTrace = ""
    currentState = None
    currentThread = None
    start = True
    for line in f.readlines():
        line = line.strip()
        if start and re_ignore_at_start.fullmatch(line):
            continue
        start = False
        m = re_trace.fullmatch(line)
        if m is None:
            if len(currentTrace) == 0 or re_eclipse_thead.fullmatch(line) is not None:
                currentThread = line
            else:
                m = re_jdk8_thread.fullmatch(line)
                if m is not None:
                    currentThread = m.group(1)
                    currentState = m.group(2)
                else:
                    if currentState is None:
                        currentState = ""
                    fullTrace = currentTrace
                    currentTrace = ""
                    traceToThread = stateToTraceToThread.get(currentState)
                    if traceToThread is None:
                        traceToThread = {}
                        stateToTraceToThread[currentState] = traceToThread
                    threads = traceToThread.get(fullTrace)
                    if threads is None:
                        threads = set()
                        traceToThread[fullTrace] = threads
                    threads.add(currentThread)
                    currentThread = None
                    currentState = None
        else:
            line = re_replace.sub("?", line)
            m = re_state.fullmatch(line)
            if m is not None:
                currentState = m.group(1)
            currentTrace += "\t" + line
            currentTrace += "\n"

    states = ["RUNNABLE", "TIMED_WAITING", "WAITING"]
    for state in stateToTraceToThread.keys():
        if state not in states:
            states += state

    for state in states:
        traceToThread = stateToTraceToThread.get(state)
        if traceToThread is None:
            continue
        traces = list(traceToThread.items())
        traces.sort(key=lambda x: -len(x[1]))
        runningTotalThreads = 0
        for trace in traces:
            print("")
            print("======================")
            print("Trace:")
            print(trace[0])
            threadCount = len(trace[1])
            runningTotalThreads += threadCount
            print("Threads ({}/{}):".format(threadCount, runningTotalThreads))
            for thread in trace[1]:
                print("\t{}".format(thread))