# TTPython Installation Script for Windows PowerShell
# Created: October 15, 2025
# Purpose: Automate TTPython setup for local development

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "    TTPython Installation Script" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Python version
Write-Host "[1/6] Checking Python version..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
Write-Host "Found: $pythonVersion" -ForegroundColor Green

if ($pythonVersion -match "Python 3\.([8-9]|1[0-9])") {
    Write-Host "[OK] Python version is compatible (3.8+)" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Python 3.8 or higher is required!" -ForegroundColor Red
    Write-Host "Please install Python 3.8+ and try again." -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 2: Clone repository
Write-Host "[2/6] Checking for TTPython repository..." -ForegroundColor Yellow

if (Test-Path "ticktalkpython") {
    Write-Host "Repository already exists. Pulling latest changes..." -ForegroundColor Yellow
    Set-Location ticktalkpython
    git pull
    Set-Location ..
} else {
    Write-Host "Cloning TTPython repository..." -ForegroundColor Yellow
    git clone https://bitbucket.org/ccsg-res/ticktalkpython.git
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Repository cloned successfully" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Failed to clone repository" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""

# Step 3: Navigate to repository and checkout tutorial branch
Write-Host "[3/6] Checking out tutorial branch..." -ForegroundColor Yellow
Set-Location ticktalkpython
git checkout tutorial

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Tutorial branch checked out" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Could not checkout tutorial branch, using current branch" -ForegroundColor Yellow
}

Write-Host ""

# Step 4: Create virtual environment
Write-Host "[4/6] Setting up virtual environment..." -ForegroundColor Yellow

$envChoice = Read-Host "Do you want to use (1) Conda or (2) Python venv? [1/2]"

if ($envChoice -eq "1") {
    Write-Host "Creating Conda environment 'ttpython'..." -ForegroundColor Yellow
    conda create -n ttpython python=3.9 -y
    Write-Host "To activate: conda activate ttpython" -ForegroundColor Cyan
    Write-Host "[WARNING] Please run 'conda activate ttpython' and then re-run this script from Step 5" -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv ttpython_env
    
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    .\ttpython_env\Scripts\Activate.ps1
    
    Write-Host "[OK] Virtual environment created and activated" -ForegroundColor Green
}

Write-Host ""

# Step 5: Install dependencies
Write-Host "[5/6] Installing dependencies..." -ForegroundColor Yellow

if (Test-Path "requirements.txt") {
    Write-Host "Installing from requirements.txt..." -ForegroundColor Yellow
    pip install -r requirements.txt
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Requirements installed" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] Some packages may have failed to install" -ForegroundColor Yellow
    }
    
    Write-Host "Installing ast_scope..." -ForegroundColor Yellow
    pip install ast_scope
    
    Write-Host "Installing jupyter (if not present)..." -ForegroundColor Yellow
    pip install jupyter
    
} else {
    Write-Host "[ERROR] requirements.txt not found!" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 6: Optional graphviz
Write-Host "[6/6] Graphviz installation (optional)..." -ForegroundColor Yellow
$graphvizChoice = Read-Host "Do you want to install graphviz support for visualization? [y/n]"

if ($graphvizChoice -eq "y" -or $graphvizChoice -eq "Y") {
    Write-Host "Note: You need to install system graphviz separately" -ForegroundColor Cyan
    Write-Host "Download from: https://graphviz.org/download/" -ForegroundColor Cyan
    Write-Host "After installing, add to PATH and run:" -ForegroundColor Cyan
    Write-Host "  pip install graphviz" -ForegroundColor Cyan
    Write-Host "  pip install pygraphviz" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "    Installation Complete!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Start Jupyter: jupyter notebook TickTalkTest.ipynb" -ForegroundColor White
Write-Host "2. Run the first two blocks to verify installation" -ForegroundColor White
Write-Host "3. Check out the CAVExamples.ipynb for tutorials" -ForegroundColor White
Write-Host ""
Write-Host "Documentation: https://ccsg.ece.cmu.edu/ttpython/" -ForegroundColor Cyan
Write-Host ""

# Return to original directory
Set-Location ..
