@echo off

CD ..

rem Cleans repo by removing everything that's not tracked in git, basically reverting to a state where the repo was just cloned
git clean -fdx