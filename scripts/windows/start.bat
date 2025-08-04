@echo off
echo Starting the Freenet Alias Adder script...
echo.

call venv\Scripts\activate
python freenet_alias_adder.py

echo.
echo Script has finished execution.
pause
