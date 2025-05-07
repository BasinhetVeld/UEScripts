cd ../..

rem Make sure git lfs is installed
git lfs install

rem Add git pre-commit hook
git config core.hooksPath .githooks/cgi

rem Check if it worked
git config --get core.hooksPath

echo "Done."
pause