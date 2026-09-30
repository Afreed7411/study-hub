pipeline {
    agent any

    environment {
        VENV = '.venv'
        PORT = '5000'
    }

    options {
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Setup') {
            steps {
                bat '''
                    if not exist "%VENV%\\Scripts\\python.exe" (
                        python -m venv %VENV%
                    )

                    %VENV%\\Scripts\\python.exe -m pip install --upgrade pip
                    %VENV%\\Scripts\\pip.exe install -r requirements-dev.txt
                '''
            }
        }

        stage('Lint') {
            steps {
                bat '''
                    %VENV%\\Scripts\\flake8.exe app tests wsgi.py --max-line-length=100
                '''
            }
        }

        stage('Test') {
            steps {
                bat '''
                    %VENV%\\Scripts\\pytest.exe tests --junitxml=test-results.xml --cov=app --cov-report=xml
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

                    if exist app.pid (
                        for /f "tokens=*" %%i in (app.pid) do taskkill /PID %%i /F 2>NUL
                        del app.pid
                    )

                    start "StudyHub" /B %VENV%\\Scripts\\python.exe wsgi.py > studyhub.log 2>&1

                    timeout /t 5 /nobreak > NUL

                    echo Application started.
                '''
            }
        }

        stage('Health Check') {
            steps {
                bat '''
                    curl.exe -f http://localhost:%PORT%/login

                    if %ERRORLEVEL% NEQ 0 (
                        echo Application health check failed.
                        exit /b 1
                    )

                    echo StudyHub is running successfully.
                '''
            }
        }
    }

    post {
        success {
            echo 'StudyHub build, tests and deployment completed successfully.'
            echo 'Application: http://localhost:5000'
        }

        failure {
            echo 'Pipeline failed - check the stage logs.'
        }
    }
}
