-- Job 관리 시스템 데이터베이스 스키마
CREATE DATABASE IF NOT EXISTS job_management;
USE job_management;

-- 사용자 테이블
CREATE TABLE Users (
    user_id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'developer', 'viewer')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Job 유형 테이블
CREATE TABLE JobTypes (
    type_id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT
);

-- 실행 유형 테이블
CREATE TABLE RunTypes (
    run_type_id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    name VARCHAR(50) NOT NULL UNIQUE
);

-- 환경 유형 테이블
CREATE TABLE EnvironmentTypes (
    env_type_id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    name VARCHAR(50) NOT NULL UNIQUE
);

-- 오류 유형 테이블
CREATE TABLE ErrorTypes (
    error_type_id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT
);

-- 에이전트 테이블
CREATE TABLE Agents (
    agent_id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    name VARCHAR(100) NOT NULL,
    hostname VARCHAR(255),
    env_type_id CHAR(36),
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (env_type_id) REFERENCES EnvironmentTypes(env_type_id)
);

-- Job 테이블
CREATE TABLE Jobs (
    job_id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    type_id CHAR(36) NOT NULL,
    owner_id CHAR(36),
    script_path VARCHAR(500),
    docker_image VARCHAR(200),
    timeout_seconds INT DEFAULT 3600,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (type_id) REFERENCES JobTypes(type_id),
    FOREIGN KEY (owner_id) REFERENCES Users(user_id) ON DELETE SET NULL
);

-- Job 스케줄 테이블
CREATE TABLE JobSchedules (
    schedule_id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    job_id CHAR(36) NOT NULL,
    cron_expression VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES Jobs(job_id) ON DELETE CASCADE
);

-- Job 실행 이력 테이블
CREATE TABLE JobRuns (
    run_id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    job_id CHAR(36) NOT NULL,
    agent_id CHAR(36),
    run_type_id CHAR(36),
    triggered_by_user_id CHAR(36),
    status VARCHAR(20) NOT NULL CHECK (status IN ('PENDING', 'RUNNING', 'SUCCESS', 'FAILED', 'CANCELLED')),
    exit_code INT,
    started_at DATETIME NOT NULL,
    finished_at DATETIME,
    FOREIGN KEY (job_id) REFERENCES Jobs(job_id),
    FOREIGN KEY (agent_id) REFERENCES Agents(agent_id) ON DELETE SET NULL,
    FOREIGN KEY (run_type_id) REFERENCES RunTypes(run_type_id),
    FOREIGN KEY (triggered_by_user_id) REFERENCES Users(user_id) ON DELETE SET NULL
);

-- Job 실행 로그 테이블
CREATE TABLE JobRunLogs (
    log_id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    run_id CHAR(36) NOT NULL,
    log_text LONGTEXT,
    log_file_path VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES JobRuns(run_id) ON DELETE CASCADE
);

-- Job 실행 오류 테이블
CREATE TABLE JobRunErrors (
    error_id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    run_id CHAR(36) NOT NULL,
    error_type_id CHAR(36),
    message TEXT NOT NULL,
    stacktrace LONGTEXT,
    occurred_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES JobRuns(run_id) ON DELETE CASCADE,
    FOREIGN KEY (error_type_id) REFERENCES ErrorTypes(error_type_id)
);

-- 감사 로그 테이블
CREATE TABLE AuditLogs (
    audit_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id CHAR(36),
    action_type VARCHAR(50) NOT NULL,
    target_type VARCHAR(50) NOT NULL,
    target_id CHAR(36),
    before_value JSON,
    after_value JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE SET NULL
);

-- 인덱스 생성
CREATE INDEX idx_jobs_owner ON Jobs(owner_id);
CREATE INDEX idx_jobs_type ON Jobs(type_id);
CREATE INDEX idx_jobs_active ON Jobs(is_active);

CREATE INDEX idx_jobruns_job_started ON JobRuns(job_id, started_at DESC);
CREATE INDEX idx_jobruns_status ON JobRuns(status);
CREATE INDEX idx_jobruns_agent ON JobRuns(agent_id);

CREATE INDEX idx_agents_active ON Agents(is_active);

CREATE INDEX idx_auditlogs_user_time ON AuditLogs(user_id, created_at DESC);
CREATE INDEX idx_auditlogs_target ON AuditLogs(target_type, target_id);

-- 기본 데이터 삽입
INSERT INTO JobTypes (name, description) VALUES 
('ETL', 'Extract, Transform, Load jobs'),
('BACKUP', 'Database and file backup jobs'),
('CLEANUP', 'Data cleanup and maintenance jobs'),
('REPORT', 'Report generation jobs');

INSERT INTO RunTypes (name) VALUES 
('MANUAL'),
('SCHEDULED'),
('RETRY');

INSERT INTO EnvironmentTypes (name) VALUES 
('DOCKER'),
('VM'),
('KUBERNETES');

INSERT INTO ErrorTypes (name, description) VALUES 
('SCRIPT_ERROR', 'Error in job script execution'),
('TIMEOUT', 'Job execution timeout'),
('RESOURCE_ERROR', 'Insufficient resources'),
('PERMISSION_ERROR', 'Permission denied');

-- 테스트 사용자 생성
INSERT INTO Users (username, email, role) VALUES 
('admin', 'admin@company.com', 'admin'),
('alice', 'alice@company.com', 'developer'),
('bob', 'bob@company.com', 'viewer');
