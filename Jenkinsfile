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
                    echo Checking Python...

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
                    echo Running Flake8...

                    "%VENV%\\Scripts\\python.exe" -m flake8 app tests wsgi.py --max-line-length=100
                '''
            }
        }

        stage('Test') {
            steps {
                bat '''
                    echo Running tests...

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
                    echo Starting StudyHub...

                    start "StudyHub" /B "%VENV%\\Scripts\\python.exe" wsgi.py > studyhub.log 2>&1

                    echo Waiting for application...
                    timeout /t 5 /nobreak > NUL
                '''
            }
        }

        stage('Health Check') {
            steps {
                bat '''
                    echo Checking StudyHub...

                    curl.exe -f http://localhost:%PORT%/login

                    if %ERRORLEVEL% NEQ 0 (
                        echo Application health check FAILED.
                        type studyhub.log
                        exit /b 1
                    )

                    echo.
                    echo ========================================
                    echo StudyHub is running successfully!
                    echo http://localhost:%PORT%
                    echo ========================================
                '''
            }
        }
    }

    post {
        success {
            echo 'StudyHub CI/CD pipeline completed successfully!'
            echo 'Application: http://localhost:5000'
        }

        failure {
            echo 'Pipeline failed - check the stage logs.'
        }
    }
}
