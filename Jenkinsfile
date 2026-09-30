pipeline {
    agent any

    environment {
        PYTHON = 'C:\\Users\\HP\\AppData\\Local\\Programs\\Python\\Python314\\python.exe'
        VENV   = '.venv'
        PORT   = '5000'
    }

    options {
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    stages {

        stage('Setup') {
            steps {
                bat '''
                    echo ========================================
                    echo Checking Python
                    echo ========================================

                    "%PYTHON%" --version

                    if not exist "%VENV%\\Scripts\\python.exe" (
                        echo Creating virtual environment...
                        "%PYTHON%" -m venv "%VENV%"
                    )

                    echo Upgrading pip...
                    "%VENV%\\Scripts\\python.exe" -m pip install --upgrade pip

                    echo Installing dependencies...
                    "%VENV%\\Scripts\\python.exe" -m pip install -r requirements-dev.txt
                '''
            }
        }

        stage('Lint') {
            steps {
                bat '''
                    echo ========================================
                    echo Running Flake8
                    echo ========================================

                    "%VENV%\\Scripts\\python.exe" -m flake8 app tests wsgi.py --max-line-length=100
                '''
            }
        }

        stage('Test') {
            steps {
                bat '''
                    echo ========================================
                    echo Running Tests
                    echo ========================================

                    "%VENV%\\Scripts\\python.exe" -m pytest tests --junitxml=test-results.xml --cov=app --cov-report=xml
                '''
            }

            post {
                always {
                    junit 'test-results.xml'
                }
            }
        }

        stage('Start Application') {
            steps {
                bat '''
                    echo ========================================
                    echo Starting StudyHub
                    echo ========================================

                    if exist studyhub.log del /F /Q studyhub.log

                    start "StudyHub" /B "%VENV%\\Scripts\\python.exe" wsgi.py > studyhub.log 2>&1

                    echo Waiting for application to start...

                    powershell -Command "Start-Sleep -Seconds 5"

                    echo Application startup completed.
                '''
            }
        }

        stage('Health Check') {
            steps {
                bat '''
                    echo ========================================
                    echo Health Check
                    echo ========================================

                    curl.exe -f http://localhost:%PORT%/login

                    if %ERRORLEVEL% NEQ 0 (
                        echo.
                        echo ========================================
                        echo APPLICATION FAILED
                        echo ========================================
                        echo.
                        echo Application logs:
                        type studyhub.log
                        exit /b 1
                    )

                    echo.
                    echo ========================================
                    echo STUDYHUB IS RUNNING
                    echo http://localhost:%PORT%
                    echo ========================================
                '''
            }
        }
    }

    post {
        success {
            echo '========================================'
            echo 'StudyHub CI/CD Pipeline SUCCESS'
            echo 'Application: http://localhost:5000'
            echo '========================================'
        }

        failure {
            echo '========================================'
            echo 'Pipeline FAILED'
            echo 'Check the stage logs.'
            echo '========================================'
        }
    }
}
