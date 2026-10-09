# Benchmark checklist

Use this before you report or act on a performance number.
Use it before you freeze a hillclimb harness.
Answer each question with evidence from a run, not a guess about code.

## Before you run

1. Write the claim in the words you would ship.
   Example: "CLI start is 30% faster at the median on the 200-file project".
   The questions test that sentence.
2. Read the measurement script. Note what it times, what it counts and what it ignores.
3. Check machine load with `uptime`. Check the core count (`nproc`, or `sysctl -n hw.ncpu` on macOS).
4. If the machine is busy, interleave the sides and say so in the report.

## The 7 questions

1. **Why not double?** Name the limiter. Profile in a run you do not report, because a profiler slows the work. If a change did not move the number, the limiter says why. Find it before you call the change useless.
2. **Was it tuned?** Run every side as production runs it. Use the release build, the same flags, the same data. Use warm or cold caches as production sees them. A side on defaults or a debug build is untuned. Tune it and measure again.
3. **Did it break limits?** Do the arithmetic. Removing a piece that is 10% of the run gives at most about 11% faster. A result past a limit means you timed something other than the work.
4. **Did it error?** Count failures. Check that the output is correct, not only present. Failed work is often fast. A book build that exits early looks quick. If the script does not count errors, add the count.
5. **Does it reproduce?** Run each side at least 5 times. Alternate A B A B. Report the median and the range. A gap smaller than the run-to-run spread is no difference.
6. **Does it matter?** Measure the end-to-end path a user waits on. A game frame is one example: time the whole frame, not one function. Report the micro result as a share of the whole.
7. **Did it happen?** Confirm the work ran inside the timed region. Look for lazy iterators nobody reads, promises nobody awaits and results the compiler can discard. Each gives a number for work that never ran.

## Report

1. Lead with the verdict: faster, slower, no measurable difference, or inconclusive.
2. Give the number with its unit, the run count, the range and the limiter.
   Example: "frame time 16.4 ms to 12.1 ms, median of 7 runs per side, range 11.8 to 12.5 ms after, bound by one physics loop on one core".
3. Call the verdict inconclusive in these cases:
   - You cannot name the limiter.
   - A side ran untuned.
   - You did not check questions 4 and 7.
4. Name the gap when the verdict is inconclusive.
5. For a quick ballpark the user asked for, one run is enough. Still check questions 4 and 7. Say it was one run.

## Fit

1. Hillclimb freezes its harness after this checklist.
2. The frozen harness prints error and work counts.
3. Each keep-or-revert then re-checks questions 4 and 7 from those counts.
