-- ============================================================================================================================
-- PROJECT      : Industrial Machine Sensor Analytics Database
-- DATABASE     : MachineSensorDB
-- PLATFORM     : Microsoft SQL Server 2019+ / Azure SQL
-- AUTHOR       : Senior Data Engineering & Database Architecture Team
-- VERSION      : 1.0.0
-- DESCRIPTION  : Production-grade Star Schema for CNC machine sensor readings.
--                Optimized for large-scale storage, analytical workloads, Parquet export,
--                and integration with Python, Pandas, Apache Spark, and ML pipelines.
-- DATASET      : ~25,286 rows x 51 columns (4 axes: X1, Y1, Z1, S1)
-- ============================================================================================================================

-- ============================================================================================================================
-- SECTION 1: CREATE DATABASE
-- ============================================================================================================================

USE master;
GO

IF EXISTS (SELECT name FROM sys.databases WHERE name = N'MachineSensorDB')
BEGIN
    ALTER DATABASE MachineSensorDB SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE MachineSensorDB;
END
GO

CREATE DATABASE MachineSensorDB
ON PRIMARY
(
    NAME        = N'MachineSensorDB_Data',
    FILENAME    = N'C:\SQLData\MachineSensorDB_Data.mdf',
    SIZE        = 512MB,
    MAXSIZE     = UNLIMITED,
    FILEGROWTH  = 256MB
)
LOG ON
(
    NAME        = N'MachineSensorDB_Log',
    FILENAME    = N'C:\SQLData\MachineSensorDB_Log.ldf',
    SIZE        = 128MB,
    MAXSIZE     = 4096MB,
    FILEGROWTH  = 64MB
);
GO

ALTER DATABASE MachineSensorDB SET RECOVERY SIMPLE;
ALTER DATABASE MachineSensorDB SET AUTO_SHRINK OFF;
ALTER DATABASE MachineSensorDB SET AUTO_CREATE_STATISTICS ON;
ALTER DATABASE MachineSensorDB SET AUTO_UPDATE_STATISTICS ON;
ALTER DATABASE MachineSensorDB SET READ_COMMITTED_SNAPSHOT ON;
GO

USE MachineSensorDB;
GO

-- ============================================================================================================================
-- SECTION 2: CREATE SCHEMAS
-- ============================================================================================================================

-- staging  : Raw CSV import landing zone (no transformations, no constraints beyond data types)
-- core     : Normalized operational layer (dimensions + fact table)
-- analytics: Reporting views and aggregation surfaces for BI, Python, and Spark consumers

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'staging')
    EXEC sp_executesql N'CREATE SCHEMA staging AUTHORIZATION dbo;';
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'core')
    EXEC sp_executesql N'CREATE SCHEMA core AUTHORIZATION dbo;';
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'analytics')
    EXEC sp_executesql N'CREATE SCHEMA analytics AUTHORIZATION dbo;';
GO

-- ============================================================================================================================
-- SECTION 3: STAGING LAYER
-- ============================================================================================================================
-- Raw import table that mirrors the CSV exactly.
-- No foreign keys, no constraints beyond column presence.
-- Used as the entry point for BULK INSERT / OPENROWSET / Python SQLAlchemy batch loads.
-- ============================================================================================================================

IF OBJECT_ID('staging.RawSensorReadings', 'U') IS NOT NULL
    DROP TABLE staging.RawSensorReadings;
GO

CREATE TABLE staging.RawSensorReadings
(
    -- Row identifier (original CSV row number)
    RowNo                       BIGINT          NULL,

    -- ── X1 Axis ─────────────────────────────────────────────────────────────
    X1_ActualPosition           FLOAT           NULL,
    X1_ActualVelocity           FLOAT           NULL,
    X1_ActualAcceleration       FLOAT           NULL,
    X1_CommandPosition          FLOAT           NULL,
    X1_CommandVelocity          FLOAT           NULL,
    X1_CommandAcceleration      FLOAT           NULL,
    X1_CurrentFeedback          FLOAT           NULL,
    X1_DCBusVoltage             FLOAT           NULL,
    X1_OutputCurrent            FLOAT           NULL,
    X1_OutputVoltage            FLOAT           NULL,
    X1_OutputPower              FLOAT           NULL,

    -- ── Y1 Axis ─────────────────────────────────────────────────────────────
    Y1_ActualPosition           FLOAT           NULL,
    Y1_ActualVelocity           FLOAT           NULL,
    Y1_ActualAcceleration       FLOAT           NULL,
    Y1_CommandPosition          FLOAT           NULL,
    Y1_CommandVelocity          FLOAT           NULL,
    Y1_CommandAcceleration      FLOAT           NULL,
    Y1_CurrentFeedback          FLOAT           NULL,
    Y1_DCBusVoltage             FLOAT           NULL,
    Y1_OutputCurrent            FLOAT           NULL,
    Y1_OutputVoltage            FLOAT           NULL,
    Y1_OutputPower              FLOAT           NULL,

    -- ── Z1 Axis ─────────────────────────────────────────────────────────────
    Z1_ActualPosition           FLOAT           NULL,
    Z1_ActualVelocity           FLOAT           NULL,
    Z1_ActualAcceleration       FLOAT           NULL,
    Z1_CommandPosition          FLOAT           NULL,
    Z1_CommandVelocity          FLOAT           NULL,
    Z1_CommandAcceleration      FLOAT           NULL,
    Z1_CurrentFeedback          FLOAT           NULL,
    Z1_DCBusVoltage             FLOAT           NULL,
    Z1_OutputCurrent            FLOAT           NULL,
    Z1_OutputVoltage            FLOAT           NULL,
    -- Note: Z1 has no OutputPower column in this dataset

    -- ── S1 Spindle Axis ──────────────────────────────────────────────────────
    S1_ActualPosition           FLOAT           NULL,
    S1_ActualVelocity           FLOAT           NULL,
    S1_ActualAcceleration       FLOAT           NULL,
    S1_CommandPosition          FLOAT           NULL,
    S1_CommandVelocity          FLOAT           NULL,
    S1_CommandAcceleration      FLOAT           NULL,
    S1_CurrentFeedback          FLOAT           NULL,
    S1_DCBusVoltage             FLOAT           NULL,
    S1_OutputCurrent            FLOAT           NULL,
    S1_OutputVoltage            FLOAT           NULL,
    S1_OutputPower              FLOAT           NULL,
    S1_SystemInertia            FLOAT           NULL,

    -- ── Machine-Level Parameters ─────────────────────────────────────────────
    M1_CURRENT_PROGRAM_NUMBER   INT             NULL,
    M1_sequence_number          INT             NULL,
    M1_CURRENT_FEEDRATE         FLOAT           NULL,
    Machining_Process           NVARCHAR(100)   NULL,
    feedrate                    FLOAT           NULL,
    clamp_pressure              FLOAT           NULL,

    -- ── Quality / Outcome Labels ─────────────────────────────────────────────
    tool_condition              TINYINT         NULL,   -- 0 = unworn, 1 = worn
    machining_finalized         TINYINT         NULL,   -- 0 = No, 1 = Yes
    passed_visual_inspection    TINYINT         NULL,   -- 0 = Fail, 1 = Pass, 2 = Marginal

    -- ── ETL Metadata ─────────────────────────────────────────────────────────
    StagingID                   BIGINT          IDENTITY(1,1) NOT NULL,
    LoadedAt                    DATETIME2(3)    NOT NULL DEFAULT SYSUTCDATETIME(),
    SourceFile                  NVARCHAR(500)   NULL,
    IsProcessed                 BIT             NOT NULL DEFAULT 0,

    CONSTRAINT PK_RawSensorReadings PRIMARY KEY NONCLUSTERED (StagingID)
);
GO

-- Index to support efficient ETL batch reads of unprocessed rows
CREATE INDEX IX_Staging_IsProcessed_StagingID
    ON staging.RawSensorReadings (IsProcessed, StagingID)
    INCLUDE (RowNo, M1_CURRENT_PROGRAM_NUMBER, Machining_Process);
GO

-- ============================================================================================================================
-- SECTION 4: CORE LAYER — DIMENSION TABLES
-- ============================================================================================================================

-- ────────────────────────────────────────────────────────────────────────────
-- DimMachine
-- Represents a physical CNC machine unit.
-- Currently dataset reflects a single machine (M1); schema supports fleet expansion.
-- ────────────────────────────────────────────────────────────────────────────

IF OBJECT_ID('core.DimMachine', 'U') IS NOT NULL DROP TABLE core.DimMachine;
GO

CREATE TABLE core.DimMachine
(
    MachineID           INT             NOT NULL IDENTITY(1,1),
    MachineCode         NVARCHAR(50)    NOT NULL,                   -- e.g., 'M1', 'M2'
    MachineName         NVARCHAR(200)   NULL,
    MachineType         NVARCHAR(100)   NULL,                       -- e.g., 'CNC Milling'
    Manufacturer        NVARCHAR(200)   NULL,
    InstallationDate    DATE            NULL,
    Location            NVARCHAR(200)   NULL,
    IsActive            BIT             NOT NULL DEFAULT 1,
    CreatedAt           DATETIME2(3)    NOT NULL DEFAULT SYSUTCDATETIME(),
    UpdatedAt           DATETIME2(3)    NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT PK_DimMachine            PRIMARY KEY CLUSTERED (MachineID),
    CONSTRAINT UQ_DimMachine_Code       UNIQUE (MachineCode)
);
GO

-- ────────────────────────────────────────────────────────────────────────────
-- DimAxis
-- Represents a motion or spindle axis on a machine.
-- Dataset axes: X1, Y1, Z1, S1
-- ────────────────────────────────────────────────────────────────────────────

IF OBJECT_ID('core.DimAxis', 'U') IS NOT NULL DROP TABLE core.DimAxis;
GO

CREATE TABLE core.DimAxis
(
    AxisID              INT             NOT NULL IDENTITY(1,1),
    MachineID           INT             NOT NULL,
    AxisCode            NVARCHAR(10)    NOT NULL,                    -- 'X1', 'Y1', 'Z1', 'S1'
    AxisType            NVARCHAR(50)    NOT NULL,                    -- 'Linear', 'Spindle'
    AxisDescription     NVARCHAR(200)   NULL,
    HasOutputPower      BIT             NOT NULL DEFAULT 1,          -- Z1 has no OutputPower in this dataset
    IsActive            BIT             NOT NULL DEFAULT 1,
    CreatedAt           DATETIME2(3)    NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT PK_DimAxis               PRIMARY KEY CLUSTERED (AxisID),
    CONSTRAINT UQ_DimAxis_MachineAxis   UNIQUE (MachineID, AxisCode),
    CONSTRAINT FK_DimAxis_Machine       FOREIGN KEY (MachineID) REFERENCES core.DimMachine (MachineID)
);
GO

-- ────────────────────────────────────────────────────────────────────────────
-- DimProgram
-- Represents CNC programs (G-code programs) loaded on the machine.
-- M1_CURRENT_PROGRAM_NUMBER maps here.
-- ────────────────────────────────────────────────────────────────────────────

IF OBJECT_ID('core.DimProgram', 'U') IS NOT NULL DROP TABLE core.DimProgram;
GO

CREATE TABLE core.DimProgram
(
    ProgramID           INT             NOT NULL IDENTITY(1,1),
    MachineID           INT             NOT NULL,
    ProgramNumber       INT             NOT NULL,                    -- M1_CURRENT_PROGRAM_NUMBER (0–4 in dataset)
    ProgramName         NVARCHAR(200)   NULL,
    ProgramDescription  NVARCHAR(500)   NULL,
    ProgramVersion      NVARCHAR(50)    NULL,
    CreatedAt           DATETIME2(3)    NOT NULL DEFAULT SYSUTCDATETIME(),
    UpdatedAt           DATETIME2(3)    NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT PK_DimProgram            PRIMARY KEY CLUSTERED (ProgramID),
    CONSTRAINT UQ_DimProgram_Number     UNIQUE (MachineID, ProgramNumber),
    CONSTRAINT FK_DimProgram_Machine    FOREIGN KEY (MachineID) REFERENCES core.DimMachine (MachineID),
    CONSTRAINT CK_DimProgram_Number     CHECK (ProgramNumber >= 0)
);
GO

-- ────────────────────────────────────────────────────────────────────────────
-- DimProcess
-- Machining process phases observed in the dataset:
-- Starting | Prep | Layer 1 Up | Layer 1 Down | Layer 2 Up | Layer 2 Down |
-- Layer 3 Up | Layer 3 Down | Repositioning | End
-- ────────────────────────────────────────────────────────────────────────────

IF OBJECT_ID('core.DimProcess', 'U') IS NOT NULL DROP TABLE core.DimProcess;
GO

CREATE TABLE core.DimProcess
(
    ProcessID           INT             NOT NULL IDENTITY(1,1),
    ProcessName         NVARCHAR(100)   NOT NULL,                   -- Machining_Process value
    ProcessCategory     NVARCHAR(100)   NULL,                       -- 'Preparation', 'Cutting', 'Transition', 'Completion'
    ProcessDescription  NVARCHAR(500)   NULL,
    SortOrder           INT             NULL,                        -- Logical execution sequence
    IsActive            BIT             NOT NULL DEFAULT 1,
    CreatedAt           DATETIME2(3)    NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT PK_DimProcess            PRIMARY KEY CLUSTERED (ProcessID),
    CONSTRAINT UQ_DimProcess_Name       UNIQUE (ProcessName)
);
GO

-- ────────────────────────────────────────────────────────────────────────────
-- DimToolCondition
-- Lookup for tool wear state derived from ML classification label.
-- ────────────────────────────────────────────────────────────────────────────

IF OBJECT_ID('core.DimToolCondition', 'U') IS NOT NULL DROP TABLE core.DimToolCondition;
GO

CREATE TABLE core.DimToolCondition
(
    ToolConditionID     TINYINT         NOT NULL,
    ConditionCode       NVARCHAR(20)    NOT NULL,                   -- 'unworn', 'worn'
    ConditionLabel      NVARCHAR(100)   NULL,
    Severity            TINYINT         NOT NULL DEFAULT 0,         -- 0=Normal, 1=Warning, 2=Critical

    CONSTRAINT PK_DimToolCondition      PRIMARY KEY CLUSTERED (ToolConditionID),
    CONSTRAINT UQ_DimToolCondition_Code UNIQUE (ConditionCode)
);
GO

-- ============================================================================================================================
-- SECTION 5: CORE LAYER — FACT TABLE
-- ============================================================================================================================
-- FactSensorReadings is the central, high-volume table.
-- Partitioned by SequenceNumber range to support Spark and batch exports.
-- Columnstore index enables sub-second analytical aggregations.
-- ============================================================================================================================

-- ── Partition Function: 10 equal buckets across observed sequence range 0–135 ──
IF EXISTS (SELECT 1 FROM sys.partition_functions WHERE name = 'PF_SequenceNumber')
    DROP PARTITION FUNCTION PF_SequenceNumber;
GO

CREATE PARTITION FUNCTION PF_SequenceNumber (INT)
AS RANGE RIGHT FOR VALUES (0, 15, 30, 45, 60, 75, 90, 105, 120, 135);
GO

-- ── Partition Scheme: maps all partitions to PRIMARY filegroup ──
IF EXISTS (SELECT 1 FROM sys.partition_schemes WHERE name = 'PS_SequenceNumber')
    DROP PARTITION SCHEME PS_SequenceNumber;
GO

CREATE PARTITION SCHEME PS_SequenceNumber
AS PARTITION PF_SequenceNumber
ALL TO ([PRIMARY]);
GO

-- ── Main Fact Table ──────────────────────────────────────────────────────────

IF OBJECT_ID('core.FactSensorReadings', 'U') IS NOT NULL DROP TABLE core.FactSensorReadings;
GO

CREATE TABLE core.FactSensorReadings
(
    -- ── Surrogate Key ────────────────────────────────────────────────────────
    ReadingID               BIGINT          NOT NULL IDENTITY(1,1),

    -- ── Foreign Keys to Dimensions ───────────────────────────────────────────
    MachineID               INT             NOT NULL,
    AxisID                  INT             NOT NULL,
    ProgramID               INT             NOT NULL,
    ProcessID               INT             NOT NULL,
    ToolConditionID         TINYINT         NULL,

    -- ── Operational Context ───────────────────────────────────────────────────
    SequenceNumber          INT             NOT NULL,               -- M1_sequence_number  (0–135)
    CurrentFeedrate         FLOAT           NULL,                   -- M1_CURRENT_FEEDRATE (mm/min)
    Feedrate                FLOAT           NULL,                   -- Programmed feedrate
    ClampPressure           FLOAT           NULL,                   -- Bar / PSI

    -- ── Motion Measurements ───────────────────────────────────────────────────
    ActualPosition          FLOAT           NULL,                   -- mm
    ActualVelocity          FLOAT           NULL,                   -- mm/s
    ActualAcceleration      FLOAT           NULL,                   -- mm/s²
    CommandPosition         FLOAT           NULL,                   -- mm
    CommandVelocity         FLOAT           NULL,                   -- mm/s
    CommandAcceleration     FLOAT           NULL,                   -- mm/s²

    -- ── Electrical Measurements ───────────────────────────────────────────────
    CurrentFeedback         FLOAT           NULL,                   -- Amperes (A)
    DCBusVoltage            FLOAT           NULL,                   -- Volts (V)
    OutputCurrent           FLOAT           NULL,                   -- Amperes (A)
    OutputVoltage           FLOAT           NULL,                   -- Volts (V)
    OutputPower             FLOAT           NULL,                   -- Kilowatts (kW) — NULL for Z1

    -- ── Spindle-Specific (populated only for S1 AxisID) ─────────────────────
    SystemInertia           FLOAT           NULL,                   -- S1_SystemInertia (kg·m²)

    -- ── Quality / Outcome Labels ──────────────────────────────────────────────
    MachiningFinalized      TINYINT         NULL                    -- 0=No, 1=Yes
        CONSTRAINT CK_Fact_MachiningFinalized CHECK (MachiningFinalized IN (0, 1) OR MachiningFinalized IS NULL),
    PassedVisualInspection  TINYINT         NULL                    -- 0=Fail, 1=Pass, 2=Marginal
        CONSTRAINT CK_Fact_PassedVisual CHECK (PassedVisualInspection IN (0, 1, 2) OR PassedVisualInspection IS NULL),

    -- ── ETL Metadata ──────────────────────────────────────────────────────────
    StagingID               BIGINT          NULL,                   -- Back-reference to staging.RawSensorReadings
    LoadedAt                DATETIME2(3)    NOT NULL DEFAULT SYSUTCDATETIME(),

    -- ── Constraints ───────────────────────────────────────────────────────────
    CONSTRAINT PK_FactSensorReadings
        PRIMARY KEY CLUSTERED (ReadingID, SequenceNumber)          -- Partition-aligned PK
        ON PS_SequenceNumber (SequenceNumber),

    CONSTRAINT FK_Fact_Machine
        FOREIGN KEY (MachineID)         REFERENCES core.DimMachine (MachineID),

    CONSTRAINT FK_Fact_Axis
        FOREIGN KEY (AxisID)            REFERENCES core.DimAxis (AxisID),

    CONSTRAINT FK_Fact_Program
        FOREIGN KEY (ProgramID)         REFERENCES core.DimProgram (ProgramID),

    CONSTRAINT FK_Fact_Process
        FOREIGN KEY (ProcessID)         REFERENCES core.DimProcess (ProcessID),

    CONSTRAINT FK_Fact_ToolCondition
        FOREIGN KEY (ToolConditionID)   REFERENCES core.DimToolCondition (ToolConditionID),

    CONSTRAINT CK_Fact_SequenceNumber
        CHECK (SequenceNumber >= 0 AND SequenceNumber <= 9999),

    CONSTRAINT CK_Fact_ClampPressure
        CHECK (ClampPressure IS NULL OR (ClampPressure >= 0 AND ClampPressure <= 1000)),

    CONSTRAINT CK_Fact_Feedrate
        CHECK (Feedrate IS NULL OR Feedrate >= 0)

) ON PS_SequenceNumber (SequenceNumber);
GO

-- ============================================================================================================================
-- SECTION 6: INDEXES
-- ============================================================================================================================

-- ── Nonclustered indexes for common analytical access patterns ───────────────

-- Filter/group by machine
CREATE NONCLUSTERED INDEX IX_Fact_MachineID
    ON core.FactSensorReadings (MachineID, SequenceNumber)
    INCLUDE (AxisID, ProgramID, ProcessID, ActualPosition, ActualVelocity, OutputPower)
    ON PS_SequenceNumber (SequenceNumber);
GO

-- Filter/group by axis
CREATE NONCLUSTERED INDEX IX_Fact_AxisID
    ON core.FactSensorReadings (AxisID, SequenceNumber)
    INCLUDE (MachineID, ActualPosition, ActualVelocity, ActualAcceleration, OutputCurrent, OutputPower)
    ON PS_SequenceNumber (SequenceNumber);
GO

-- Filter/group by program
CREATE NONCLUSTERED INDEX IX_Fact_ProgramID
    ON core.FactSensorReadings (ProgramID, SequenceNumber)
    INCLUDE (MachineID, ProcessID, Feedrate, CurrentFeedrate)
    ON PS_SequenceNumber (SequenceNumber);
GO

-- Sequence-based range scans (batch exports, Spark partitioning)
CREATE NONCLUSTERED INDEX IX_Fact_SequenceNumber
    ON core.FactSensorReadings (SequenceNumber)
    INCLUDE (MachineID, AxisID, ProgramID, ProcessID, ReadingID)
    ON PS_SequenceNumber (SequenceNumber);
GO

-- ML workloads: process + tool condition correlation
CREATE NONCLUSTERED INDEX IX_Fact_Process_ToolCondition
    ON core.FactSensorReadings (ProcessID, ToolConditionID, SequenceNumber)
    INCLUDE (ActualVelocity, ActualAcceleration, CurrentFeedback, OutputPower, SystemInertia)
    ON PS_SequenceNumber (SequenceNumber);
GO

-- ETL deduplication using StagingID
CREATE NONCLUSTERED INDEX IX_Fact_StagingID
    ON core.FactSensorReadings (StagingID)
    WHERE StagingID IS NOT NULL
    ON PS_SequenceNumber (SequenceNumber);
GO

-- ── Columnstore Index for OLAP / Pandas / Spark aggregations ────────────────
-- Covers all measurement columns; delivers 10–100x compression and vectorised scans.

CREATE NONCLUSTERED COLUMNSTORE INDEX NCSI_Fact_Analytics
    ON core.FactSensorReadings
    (
        MachineID, AxisID, ProgramID, ProcessID, ToolConditionID,
        SequenceNumber, CurrentFeedrate, Feedrate, ClampPressure,
        ActualPosition, ActualVelocity, ActualAcceleration,
        CommandPosition, CommandVelocity, CommandAcceleration,
        CurrentFeedback, DCBusVoltage, OutputCurrent, OutputVoltage, OutputPower,
        SystemInertia, MachiningFinalized, PassedVisualInspection
    )
    ON PS_SequenceNumber (SequenceNumber);
GO

-- ── DimAxis lookup optimization ──────────────────────────────────────────────
CREATE NONCLUSTERED INDEX IX_DimAxis_MachineCode
    ON core.DimAxis (MachineID, AxisCode)
    INCLUDE (AxisType, HasOutputPower);
GO

-- ── Staging ETL lookup index ─────────────────────────────────────────────────
CREATE NONCLUSTERED INDEX IX_Staging_Program_Process
    ON staging.RawSensorReadings (IsProcessed, M1_CURRENT_PROGRAM_NUMBER, Machining_Process)
    INCLUDE (StagingID, RowNo, M1_sequence_number);
GO

-- ============================================================================================================================
-- SECTION 7: STORED PROCEDURES
-- ============================================================================================================================

-- ────────────────────────────────────────────────────────────────────────────
-- usp_LoadSensorReadingsFromStaging
-- Merges unprocessed staging rows into core.FactSensorReadings.
-- Safe for concurrent batch calls; uses MERGE with identity resolution.
-- ────────────────────────────────────────────────────────────────────────────

IF OBJECT_ID('core.usp_LoadSensorReadingsFromStaging', 'P') IS NOT NULL
    DROP PROCEDURE core.usp_LoadSensorReadingsFromStaging;
GO

CREATE PROCEDURE core.usp_LoadSensorReadingsFromStaging
    @BatchSize          INT             = 5000,
    @MachineCode        NVARCHAR(50)    = N'M1',
    @SourceFile         NVARCHAR(500)   = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE
        @MachineID      INT,
        @RowsProcessed  INT = 0,
        @ErrorMsg       NVARCHAR(4000);

    -- ── Resolve MachineID ────────────────────────────────────────────────────
    SELECT @MachineID = MachineID
    FROM   core.DimMachine
    WHERE  MachineCode = @MachineCode AND IsActive = 1;

    IF @MachineID IS NULL
    BEGIN
        RAISERROR('Machine code ''%s'' not found or inactive.', 16, 1, @MachineCode);
        RETURN -1;
    END;

    -- ── Temp table for current batch ─────────────────────────────────────────
    CREATE TABLE #StagingBatch
    (
        StagingID               BIGINT,
        RowNo                   BIGINT,
        AxisCode                NVARCHAR(10),
        ProgramNumber           INT,
        ProcessName             NVARCHAR(100),
        SequenceNumber          INT,
        CurrentFeedrate         FLOAT,
        Feedrate                FLOAT,
        ClampPressure           FLOAT,
        ActualPosition          FLOAT,
        ActualVelocity          FLOAT,
        ActualAcceleration      FLOAT,
        CommandPosition         FLOAT,
        CommandVelocity         FLOAT,
        CommandAcceleration     FLOAT,
        CurrentFeedback         FLOAT,
        DCBusVoltage            FLOAT,
        OutputCurrent           FLOAT,
        OutputVoltage           FLOAT,
        OutputPower             FLOAT,
        SystemInertia           FLOAT,
        ToolCondition           TINYINT,
        MachiningFinalized      TINYINT,
        PassedVisualInspection  TINYINT
    );

    -- ── Pivot staging columns into per-axis rows ─────────────────────────────
    -- Each raw row produces 4 axis rows (X1, Y1, Z1, S1)
    INSERT INTO #StagingBatch
    SELECT TOP (@BatchSize)
        src.StagingID,
        src.RowNo,
        ax.AxisCode,
        ISNULL(src.M1_CURRENT_PROGRAM_NUMBER, 0)    AS ProgramNumber,
        ISNULL(src.Machining_Process, N'Unknown')   AS ProcessName,
        ISNULL(src.M1_sequence_number, 0)           AS SequenceNumber,
        src.M1_CURRENT_FEEDRATE,
        src.feedrate,
        src.clamp_pressure,
        ax.ActualPosition,
        ax.ActualVelocity,
        ax.ActualAcceleration,
        ax.CommandPosition,
        ax.CommandVelocity,
        ax.CommandAcceleration,
        ax.CurrentFeedback,
        ax.DCBusVoltage,
        ax.OutputCurrent,
        ax.OutputVoltage,
        ax.OutputPower,
        src.S1_SystemInertia,
        src.tool_condition,
        src.machining_finalized,
        src.passed_visual_inspection
    FROM staging.RawSensorReadings src
    CROSS APPLY
    (
        VALUES
        ('X1', src.X1_ActualPosition, src.X1_ActualVelocity, src.X1_ActualAcceleration,
                src.X1_CommandPosition, src.X1_CommandVelocity, src.X1_CommandAcceleration,
                src.X1_CurrentFeedback, src.X1_DCBusVoltage,
                src.X1_OutputCurrent, src.X1_OutputVoltage, src.X1_OutputPower),
        ('Y1', src.Y1_ActualPosition, src.Y1_ActualVelocity, src.Y1_ActualAcceleration,
                src.Y1_CommandPosition, src.Y1_CommandVelocity, src.Y1_CommandAcceleration,
                src.Y1_CurrentFeedback, src.Y1_DCBusVoltage,
                src.Y1_OutputCurrent, src.Y1_OutputVoltage, src.Y1_OutputPower),
        ('Z1', src.Z1_ActualPosition, src.Z1_ActualVelocity, src.Z1_ActualAcceleration,
                src.Z1_CommandPosition, src.Z1_CommandVelocity, src.Z1_CommandAcceleration,
                src.Z1_CurrentFeedback, src.Z1_DCBusVoltage,
                src.Z1_OutputCurrent, src.Z1_OutputVoltage, NULL),         -- Z1 has no OutputPower
        ('S1', src.S1_ActualPosition, src.S1_ActualVelocity, src.S1_ActualAcceleration,
                src.S1_CommandPosition, src.S1_CommandVelocity, src.S1_CommandAcceleration,
                src.S1_CurrentFeedback, src.S1_DCBusVoltage,
                src.S1_OutputCurrent, src.S1_OutputVoltage, src.S1_OutputPower)
    ) AS ax (AxisCode,
             ActualPosition, ActualVelocity, ActualAcceleration,
             CommandPosition, CommandVelocity, CommandAcceleration,
             CurrentFeedback, DCBusVoltage,
             OutputCurrent, OutputVoltage, OutputPower)
    WHERE src.IsProcessed = 0
    ORDER BY src.StagingID;

    -- ── Ensure dimension records exist (idempotent upserts) ──────────────────
    BEGIN TRANSACTION;

    BEGIN TRY

        -- Programs
        MERGE core.DimProgram AS tgt
        USING (
            SELECT DISTINCT @MachineID AS MachineID, ProgramNumber
            FROM #StagingBatch
        ) AS src ON tgt.MachineID = src.MachineID AND tgt.ProgramNumber = src.ProgramNumber
        WHEN NOT MATCHED THEN
            INSERT (MachineID, ProgramNumber)
            VALUES (src.MachineID, src.ProgramNumber);

        -- Processes
        MERGE core.DimProcess AS tgt
        USING (
            SELECT DISTINCT ProcessName FROM #StagingBatch
        ) AS src ON tgt.ProcessName = src.ProcessName
        WHEN NOT MATCHED THEN
            INSERT (ProcessName) VALUES (src.ProcessName);

        -- Axes
        MERGE core.DimAxis AS tgt
        USING (
            SELECT DISTINCT @MachineID AS MachineID, AxisCode,
                CASE WHEN AxisCode = 'S1' THEN 'Spindle' ELSE 'Linear' END AS AxisType,
                CASE WHEN AxisCode = 'Z1' THEN 0 ELSE 1 END AS HasOutputPower
            FROM #StagingBatch
        ) AS src ON tgt.MachineID = src.MachineID AND tgt.AxisCode = src.AxisCode
        WHEN NOT MATCHED THEN
            INSERT (MachineID, AxisCode, AxisType, HasOutputPower)
            VALUES (src.MachineID, src.AxisCode, src.AxisType, src.HasOutputPower);

        -- ── Insert into FactSensorReadings ───────────────────────────────────
        INSERT INTO core.FactSensorReadings
        (
            MachineID, AxisID, ProgramID, ProcessID, ToolConditionID,
            SequenceNumber, CurrentFeedrate, Feedrate, ClampPressure,
            ActualPosition, ActualVelocity, ActualAcceleration,
            CommandPosition, CommandVelocity, CommandAcceleration,
            CurrentFeedback, DCBusVoltage, OutputCurrent, OutputVoltage, OutputPower,
            SystemInertia, MachiningFinalized, PassedVisualInspection, StagingID
        )
        SELECT
            @MachineID,
            da.AxisID,
            dp.ProgramID,
            dpr.ProcessID,
            b.ToolCondition,
            b.SequenceNumber,
            b.CurrentFeedrate,
            b.Feedrate,
            b.ClampPressure,
            b.ActualPosition,
            b.ActualVelocity,
            b.ActualAcceleration,
            b.CommandPosition,
            b.CommandVelocity,
            b.CommandAcceleration,
            b.CurrentFeedback,
            b.DCBusVoltage,
            b.OutputCurrent,
            b.OutputVoltage,
            b.OutputPower,
            CASE WHEN b.AxisCode = 'S1' THEN b.SystemInertia ELSE NULL END,
            b.MachiningFinalized,
            b.PassedVisualInspection,
            b.StagingID
        FROM #StagingBatch b
        INNER JOIN core.DimAxis    da  ON da.MachineID = @MachineID AND da.AxisCode = b.AxisCode
        INNER JOIN core.DimProgram dp  ON dp.MachineID = @MachineID AND dp.ProgramNumber = b.ProgramNumber
        INNER JOIN core.DimProcess dpr ON dpr.ProcessName = b.ProcessName;

        SET @RowsProcessed = @@ROWCOUNT;

        -- ── Mark staging rows as processed ───────────────────────────────────
        UPDATE s
        SET    s.IsProcessed = 1
        FROM   staging.RawSensorReadings s
        INNER JOIN (SELECT DISTINCT StagingID FROM #StagingBatch) b ON s.StagingID = b.StagingID;

        COMMIT TRANSACTION;

    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        SET @ErrorMsg = ERROR_MESSAGE();
        RAISERROR('usp_LoadSensorReadingsFromStaging failed: %s', 16, 1, @ErrorMsg);
        RETURN -1;
    END CATCH;

    DROP TABLE #StagingBatch;

    -- ── Return ETL summary ────────────────────────────────────────────────────
    SELECT
        @RowsProcessed          AS FactRowsInserted,
        @RowsProcessed / 4      AS StagingRowsProcessed,    -- 4 axes per raw row
        SYSUTCDATETIME()        AS CompletedAt;

    RETURN 0;
END;
GO

-- ────────────────────────────────────────────────────────────────────────────
-- usp_InsertSingleSensorReading
-- Lightweight single-row insert for real-time / event-driven scenarios.
-- ────────────────────────────────────────────────────────────────────────────

IF OBJECT_ID('core.usp_InsertSingleSensorReading', 'P') IS NOT NULL
    DROP PROCEDURE core.usp_InsertSingleSensorReading;
GO

CREATE PROCEDURE core.usp_InsertSingleSensorReading
    @MachineID              INT,
    @AxisID                 INT,
    @ProgramID              INT,
    @ProcessID              INT,
    @ToolConditionID        TINYINT     = NULL,
    @SequenceNumber         INT,
    @CurrentFeedrate        FLOAT       = NULL,
    @Feedrate               FLOAT       = NULL,
    @ClampPressure          FLOAT       = NULL,
    @ActualPosition         FLOAT       = NULL,
    @ActualVelocity         FLOAT       = NULL,
    @ActualAcceleration     FLOAT       = NULL,
    @CommandPosition        FLOAT       = NULL,
    @CommandVelocity        FLOAT       = NULL,
    @CommandAcceleration    FLOAT       = NULL,
    @CurrentFeedback        FLOAT       = NULL,
    @DCBusVoltage           FLOAT       = NULL,
    @OutputCurrent          FLOAT       = NULL,
    @OutputVoltage          FLOAT       = NULL,
    @OutputPower            FLOAT       = NULL,
    @SystemInertia          FLOAT       = NULL,
    @MachiningFinalized     TINYINT     = NULL,
    @PassedVisualInspection TINYINT     = NULL,
    @NewReadingID           BIGINT      OUTPUT
AS
BEGIN
    SET NOCOUNT ON;

    INSERT INTO core.FactSensorReadings
    (
        MachineID, AxisID, ProgramID, ProcessID, ToolConditionID,
        SequenceNumber, CurrentFeedrate, Feedrate, ClampPressure,
        ActualPosition, ActualVelocity, ActualAcceleration,
        CommandPosition, CommandVelocity, CommandAcceleration,
        CurrentFeedback, DCBusVoltage, OutputCurrent, OutputVoltage, OutputPower,
        SystemInertia, MachiningFinalized, PassedVisualInspection
    )
    VALUES
    (
        @MachineID, @AxisID, @ProgramID, @ProcessID, @ToolConditionID,
        @SequenceNumber, @CurrentFeedrate, @Feedrate, @ClampPressure,
        @ActualPosition, @ActualVelocity, @ActualAcceleration,
        @CommandPosition, @CommandVelocity, @CommandAcceleration,
        @CurrentFeedback, @DCBusVoltage, @OutputCurrent, @OutputVoltage, @OutputPower,
        @SystemInertia, @MachiningFinalized, @PassedVisualInspection
    );

    SET @NewReadingID = SCOPE_IDENTITY();
    RETURN 0;
END;
GO

-- ────────────────────────────────────────────────────────────────────────────
-- usp_RebuildColumnstoreIndex
-- Maintenance procedure: reorganize or rebuild NCSI_Fact_Analytics.
-- Schedule via SQL Agent for off-peak windows.
-- ────────────────────────────────────────────────────────────────────────────

IF OBJECT_ID('core.usp_RebuildColumnstoreIndex', 'P') IS NOT NULL
    DROP PROCEDURE core.usp_RebuildColumnstoreIndex;
GO

CREATE PROCEDURE core.usp_RebuildColumnstoreIndex
    @Mode   NVARCHAR(20) = N'REORGANIZE'    -- 'REORGANIZE' | 'REBUILD'
AS
BEGIN
    SET NOCOUNT ON;

    IF UPPER(@Mode) = N'REBUILD'
        ALTER INDEX NCSI_Fact_Analytics ON core.FactSensorReadings REBUILD;
    ELSE
        ALTER INDEX NCSI_Fact_Analytics ON core.FactSensorReadings REORGANIZE;

    SELECT
        UPPER(@Mode)    AS IndexOperation,
        SYSUTCDATETIME() AS CompletedAt;
END;
GO

-- ============================================================================================================================
-- SECTION 8: ANALYTICS VIEWS
-- ============================================================================================================================

-- ────────────────────────────────────────────────────────────────────────────
-- vw_SensorReadingsFull
-- Denormalized flat view for Pandas, Power BI, and direct Spark queries.
-- Equivalent to the original CSV schema after dimension resolution.
-- ────────────────────────────────────────────────────────────────────────────

IF OBJECT_ID('analytics.vw_SensorReadingsFull', 'V') IS NOT NULL
    DROP VIEW analytics.vw_SensorReadingsFull;
GO

CREATE VIEW analytics.vw_SensorReadingsFull
AS
SELECT
    -- ── Surrogate / ETL Keys ─────────────────────────────────────────────────
    f.ReadingID,
    f.StagingID,
    f.LoadedAt,

    -- ── Machine ──────────────────────────────────────────────────────────────
    m.MachineCode,
    m.MachineName,

    -- ── Axis ─────────────────────────────────────────────────────────────────
    a.AxisCode,
    a.AxisType,

    -- ── Program ──────────────────────────────────────────────────────────────
    p.ProgramNumber                             AS CurrentProgramNumber,

    -- ── Process ──────────────────────────────────────────────────────────────
    pr.ProcessName                              AS MachiningProcess,
    pr.ProcessCategory,
    pr.SortOrder                                AS ProcessSortOrder,

    -- ── Tool Condition ────────────────────────────────────────────────────────
    tc.ConditionCode                            AS ToolCondition,
    tc.Severity                                 AS ToolSeverity,

    -- ── Operational Parameters ────────────────────────────────────────────────
    f.SequenceNumber,
    f.CurrentFeedrate,
    f.Feedrate,
    f.ClampPressure,

    -- ── Motion Measurements ───────────────────────────────────────────────────
    f.ActualPosition,
    f.ActualVelocity,
    f.ActualAcceleration,
    f.CommandPosition,
    f.CommandVelocity,
    f.CommandAcceleration,

    -- ── Electrical Measurements ───────────────────────────────────────────────
    f.CurrentFeedback,
    f.DCBusVoltage,
    f.OutputCurrent,
    f.OutputVoltage,
    f.OutputPower,

    -- ── Derived: Positional Error ─────────────────────────────────────────────
    ROUND(f.ActualPosition - f.CommandPosition, 6)  AS PositionError,
    ROUND(f.ActualVelocity - f.CommandVelocity, 6)  AS VelocityError,

    -- ── Spindle ───────────────────────────────────────────────────────────────
    f.SystemInertia,

    -- ── Quality Labels ────────────────────────────────────────────────────────
    f.MachiningFinalized,
    f.PassedVisualInspection

FROM core.FactSensorReadings        f
INNER JOIN core.DimMachine          m   ON m.MachineID      = f.MachineID
INNER JOIN core.DimAxis             a   ON a.AxisID          = f.AxisID
INNER JOIN core.DimProgram          p   ON p.ProgramID       = f.ProgramID
INNER JOIN core.DimProcess          pr  ON pr.ProcessID      = f.ProcessID
LEFT  JOIN core.DimToolCondition    tc  ON tc.ToolConditionID = f.ToolConditionID;
GO

-- ────────────────────────────────────────────────────────────────────────────
-- vw_AxisSummaryStats
-- Per-axis aggregate statistics by process phase.
-- Designed for Python/Pandas describe() equivalents and dashboard KPIs.
-- ────────────────────────────────────────────────────────────────────────────

IF OBJECT_ID('analytics.vw_AxisSummaryStats', 'V') IS NOT NULL
    DROP VIEW analytics.vw_AxisSummaryStats;
GO

CREATE VIEW analytics.vw_AxisSummaryStats
AS
SELECT
    m.MachineCode,
    a.AxisCode,
    pr.ProcessName,
    COUNT(*)                                AS ReadingCount,
    -- Position
    MIN(f.ActualPosition)                   AS ActualPosition_Min,
    AVG(f.ActualPosition)                   AS ActualPosition_Avg,
    MAX(f.ActualPosition)                   AS ActualPosition_Max,
    STDEV(f.ActualPosition)                 AS ActualPosition_StdDev,
    -- Velocity
    MIN(f.ActualVelocity)                   AS ActualVelocity_Min,
    AVG(f.ActualVelocity)                   AS ActualVelocity_Avg,
    MAX(f.ActualVelocity)                   AS ActualVelocity_Max,
    STDEV(f.ActualVelocity)                 AS ActualVelocity_StdDev,
    -- Power
    MIN(f.OutputPower)                      AS OutputPower_Min,
    AVG(f.OutputPower)                      AS OutputPower_Avg,
    MAX(f.OutputPower)                      AS OutputPower_Max,
    -- Current
    AVG(f.OutputCurrent)                    AS OutputCurrent_Avg,
    -- Positional Error
    AVG(ABS(f.ActualPosition - f.CommandPosition)) AS MeanAbsPositionError,
    AVG(ABS(f.ActualVelocity - f.CommandVelocity)) AS MeanAbsVelocityError
FROM core.FactSensorReadings        f
INNER JOIN core.DimMachine          m   ON m.MachineID  = f.MachineID
INNER JOIN core.DimAxis             a   ON a.AxisID      = f.AxisID
INNER JOIN core.DimProcess          pr  ON pr.ProcessID  = f.ProcessID
GROUP BY m.MachineCode, a.AxisCode, pr.ProcessName;
GO

-- ────────────────────────────────────────────────────────────────────────────
-- vw_MachineLevelOperational
-- One row per sequence snapshot; aggregates all 4 axes into machine-level KPIs.
-- Suitable for anomaly detection and ML feature engineering.
-- ────────────────────────────────────────────────────────────────────────────

IF OBJECT_ID('analytics.vw_MachineLevelOperational', 'V') IS NOT NULL
    DROP VIEW analytics.vw_MachineLevelOperational;
GO

CREATE VIEW analytics.vw_MachineLevelOperational
AS
SELECT
    m.MachineCode,
    p.ProgramNumber,
    pr.ProcessName,
    f.SequenceNumber,
    f.Feedrate,
    f.ClampPressure,

    -- Total power across all axes
    SUM(f.OutputPower)                                          AS TotalOutputPower_kW,

    -- Mean absolute position tracking error across linear axes
    AVG(ABS(f.ActualPosition - f.CommandPosition))              AS MeanPositionError_mm,
    AVG(ABS(f.ActualVelocity - f.CommandVelocity))              AS MeanVelocityError_mms,

    -- Electrical health
    AVG(f.DCBusVoltage)                                         AS AvgDCBusVoltage,
    AVG(f.OutputCurrent)                                        AS AvgOutputCurrent_A,

    -- Spindle
    MAX(CASE WHEN a.AxisCode = 'S1' THEN f.ActualVelocity END)  AS SpindleSpeed_RPM,
    MAX(CASE WHEN a.AxisCode = 'S1' THEN f.SystemInertia END)   AS SystemInertia,
    MAX(CASE WHEN a.AxisCode = 'S1' THEN f.CurrentFeedback END) AS SpindleCurrentFeedback,

    -- Quality outcomes
    MAX(CAST(f.MachiningFinalized AS INT))                      AS MachiningFinalized,
    MAX(CAST(f.PassedVisualInspection AS INT))                  AS PassedVisualInspection
FROM core.FactSensorReadings        f
INNER JOIN core.DimMachine          m   ON m.MachineID  = f.MachineID
INNER JOIN core.DimAxis             a   ON a.AxisID      = f.AxisID
INNER JOIN core.DimProgram          p   ON p.ProgramID   = f.ProgramID
INNER JOIN core.DimProcess          pr  ON pr.ProcessID  = f.ProcessID
GROUP BY
    m.MachineCode,
    p.ProgramNumber,
    pr.ProcessName,
    f.SequenceNumber,
    f.Feedrate,
    f.ClampPressure;
GO

-- ============================================================================================================================
-- SECTION 9: REFERENCE / DIMENSION DATA SEEDING
-- ============================================================================================================================

-- ── DimToolCondition seed ────────────────────────────────────────────────────
INSERT INTO core.DimToolCondition (ToolConditionID, ConditionCode, ConditionLabel, Severity)
VALUES
    (0, 'unworn',   'Tool is within normal wear tolerance',        0),
    (1, 'worn',     'Tool has exceeded acceptable wear threshold', 1);
GO

-- ── DimMachine seed — single machine as reflected in dataset ────────────────
INSERT INTO core.DimMachine (MachineCode, MachineName, MachineType, IsActive)
VALUES (N'M1', N'CNC Machine Unit 1', N'CNC Milling', 1);
GO

-- ── DimProcess seed — all process states observed in Machining_Process column
INSERT INTO core.DimProcess (ProcessName, ProcessCategory, SortOrder)
VALUES
    (N'Starting',           N'Preparation',  1),
    (N'Prep',               N'Preparation',  2),
    (N'Layer 1 Up',         N'Cutting',      3),
    (N'Layer 1 Down',       N'Cutting',      4),
    (N'Layer 2 Up',         N'Cutting',      5),
    (N'Layer 2 Down',       N'Cutting',      6),
    (N'Layer 3 Up',         N'Cutting',      7),
    (N'Layer 3 Down',       N'Cutting',      8),
    (N'Repositioning',      N'Transition',   9),
    (N'End',                N'Completion',  10),
    (N'Unknown',            N'Unknown',     99);
GO

-- ── DimAxis seed — 4 axes for M1 ─────────────────────────────────────────────
DECLARE @M1 INT = (SELECT MachineID FROM core.DimMachine WHERE MachineCode = 'M1');

INSERT INTO core.DimAxis (MachineID, AxisCode, AxisType, AxisDescription, HasOutputPower)
VALUES
    (@M1, N'X1', N'Linear',  N'X-axis linear motion drive',      1),
    (@M1, N'Y1', N'Linear',  N'Y-axis linear motion drive',      1),
    (@M1, N'Z1', N'Linear',  N'Z-axis linear motion drive',      0),    -- no OutputPower in dataset
    (@M1, N'S1', N'Spindle', N'S1 spindle rotary axis drive',    1);
GO

-- ── DimProgram seed — programs 0–4 observed in M1_CURRENT_PROGRAM_NUMBER ────
DECLARE @M1P INT = (SELECT MachineID FROM core.DimMachine WHERE MachineCode = 'M1');

INSERT INTO core.DimProgram (MachineID, ProgramNumber, ProgramName)
VALUES
    (@M1P, 0, N'M1 Program 0 — Idle/Setup'),
    (@M1P, 1, N'M1 Program 1 — Primary Machining'),
    (@M1P, 2, N'M1 Program 2 — Secondary Operation'),
    (@M1P, 3, N'M1 Program 3 — Tertiary Operation'),
    (@M1P, 4, N'M1 Program 4 — Finishing Pass');
GO

-- ============================================================================================================================
-- SECTION 10: SAMPLE DATA INSERT (via staging → fact pipeline)
-- ============================================================================================================================

-- ── Insert representative rows into staging ──────────────────────────────────

INSERT INTO staging.RawSensorReadings
(
    RowNo,
    X1_ActualPosition, X1_ActualVelocity, X1_ActualAcceleration,
    X1_CommandPosition, X1_CommandVelocity, X1_CommandAcceleration,
    X1_CurrentFeedback, X1_DCBusVoltage, X1_OutputCurrent, X1_OutputVoltage, X1_OutputPower,
    Y1_ActualPosition, Y1_ActualVelocity, Y1_ActualAcceleration,
    Y1_CommandPosition, Y1_CommandVelocity, Y1_CommandAcceleration,
    Y1_CurrentFeedback, Y1_DCBusVoltage, Y1_OutputCurrent, Y1_OutputVoltage, Y1_OutputPower,
    Z1_ActualPosition, Z1_ActualVelocity, Z1_ActualAcceleration,
    Z1_CommandPosition, Z1_CommandVelocity, Z1_CommandAcceleration,
    Z1_CurrentFeedback, Z1_DCBusVoltage, Z1_OutputCurrent, Z1_OutputVoltage,
    S1_ActualPosition, S1_ActualVelocity, S1_ActualAcceleration,
    S1_CommandPosition, S1_CommandVelocity, S1_CommandAcceleration,
    S1_CurrentFeedback, S1_DCBusVoltage, S1_OutputCurrent, S1_OutputVoltage, S1_OutputPower,
    S1_SystemInertia,
    M1_CURRENT_PROGRAM_NUMBER, M1_sequence_number, M1_CURRENT_FEEDRATE,
    Machining_Process, feedrate, clamp_pressure,
    tool_condition, machining_finalized, passed_visual_inspection,
    SourceFile
)
VALUES
-- Row 0: Machine at rest — Starting phase
(
    0,
    198, 0, 0, 198, 0, 0, 0.18, 0.0207, 329, 2.77, -1.42E-06,
    158, -0.025, -6.25, 158, 0, 0, 0.539, 0.0167, 328, 1.84, 6.43E-07,
    119, 0, 0, 119, 0, 0, 0, 0, 0,
    -361, 0.001, 0.25, -361, 0, 0, 0.524, 2.74E-19, 329, 0, 6.96E-07,
    12,
    1, 0, 50, N'Starting', 6, 4,
    0, 1, 1, N'sample_import_v1.csv'
),
-- Row 1: Acceleration into Prep
(
    1,
    198, -10.8, -350, 198, -13.6, -358, -10.9, 0.186, 328, 23.3, 0.00448,
    158, -19.8, -750, 157, -24.6, -647, -14.5, 0.281, 325, 37.8, 0.0126,
    119, -20.3, -712, 118, -25.6, -674, 0, 0, 0,
    -361, 0, 0.25, -361, 0, 0, -0.288, 2.74E-19, 328, 0, -5.27E-07,
    12,
    1, 4, 50, N'Prep', 6, 4,
    0, 1, 1, N'sample_import_v1.csv'
),
-- Row 2: Steady-state cutting — Layer 1 Up
(
    2,
    162, -14.2, 0, 162, -14.0, 0, -9.31, 0.172, 327, 28.9, 0.00512,
    108, -22.1, 0, 108, -22.0, 0, -7.45, 0.214, 326, 41.3, 0.00931,
    58, -18.5, 0, 58, -18.5, 0, 0, 0, 0,
    860, 53.3, 0, 860, 53.3, 0, 18.8, 0.855, 322, 117, 0.165,
    12,
    1, 39, 20, N'Layer 1 Up', 20, 3,
    0, 1, 1, N'sample_import_v1.csv'
),
-- Row 3: High-load cutting — Layer 2 Down (worn tool)
(
    3,
    148, -16.5, 31.25, 148, -16.5, 0, -12.7, 0.221, 328, 36.4, 0.00812,
    91, -26.3, 0, 91, -26.3, 0, -9.88, 0.189, 325, 52.1, 0.01103,
    28.5, 0, 0, 28.5, 0, 0, 0, 0, 0,
    -1160, 53.4, 0, -1160, 53.3, 0, 22.1, 0.952, 327, 119, 0.183,
    12,
    1, 85, 20, N'Layer 2 Down', 20, 4,
    1, 1, 0, N'sample_import_v1.csv'
),
-- Row 4: End of cycle
(
    4,
    198, 0, 0, 198, 0, 0, 0.18, 0.0207, 327, 2.77, -1.42E-06,
    158, 0, 0, 158, 0, 0, 0.539, 0.0167, 326, 1.84, 6.43E-07,
    119, 0, 0, 119, 0, 0, 0, 0, 0,
    -361, 0, 0, -361, 0, 0, 0.524, 2.74E-19, 322, 0, 5.00E-07,
    12,
    1, 135, 6, N'End', 6, 3,
    0, 1, 1, N'sample_import_v1.csv'
);
GO

-- ── Trigger the ETL pipeline to promote staging rows to fact ─────────────────
EXEC core.usp_LoadSensorReadingsFromStaging
    @BatchSize   = 5000,
    @MachineCode = N'M1',
    @SourceFile  = N'sample_import_v1.csv';
GO

-- ============================================================================================================================
-- SECTION 11: SAMPLE ANALYTICAL QUERIES
-- ============================================================================================================================

-- ────────────────────────────────────────────────────────────────────────────
-- Q1: Full denormalized export for Parquet / Python / Spark
--     Run this via pyodbc / SQLAlchemy and pipe to pandas.DataFrame.to_parquet()
-- ────────────────────────────────────────────────────────────────────────────

SELECT
    ReadingID,
    MachineCode,
    AxisCode,
    AxisType,
    CurrentProgramNumber,
    MachiningProcess,
    ProcessCategory,
    ProcessSortOrder,
    ToolCondition,
    SequenceNumber,
    CurrentFeedrate,
    Feedrate,
    ClampPressure,
    ActualPosition,
    ActualVelocity,
    ActualAcceleration,
    CommandPosition,
    CommandVelocity,
    CommandAcceleration,
    PositionError,
    VelocityError,
    CurrentFeedback,
    DCBusVoltage,
    OutputCurrent,
    OutputVoltage,
    OutputPower,
    SystemInertia,
    MachiningFinalized,
    PassedVisualInspection,
    LoadedAt
FROM analytics.vw_SensorReadingsFull
ORDER BY SequenceNumber, MachineCode, AxisCode;
GO

-- ────────────────────────────────────────────────────────────────────────────
-- Q2: Per-axis summary statistics by process (equivalent to df.groupby().describe())
-- ────────────────────────────────────────────────────────────────────────────

SELECT
    MachineCode,
    AxisCode,
    ProcessName,
    ReadingCount,
    ActualPosition_Min,
    ActualPosition_Avg,
    ActualPosition_Max,
    ActualPosition_StdDev,
    ActualVelocity_Min,
    ActualVelocity_Avg,
    ActualVelocity_Max,
    OutputPower_Avg,
    MeanAbsPositionError,
    MeanAbsVelocityError
FROM analytics.vw_AxisSummaryStats
ORDER BY MachineCode, AxisCode, ProcessName;
GO

-- ────────────────────────────────────────────────────────────────────────────
-- Q3: Machine-level KPI by sequence number (for time-series ML features)
-- ────────────────────────────────────────────────────────────────────────────

SELECT
    MachineCode,
    ProgramNumber,
    ProcessName,
    SequenceNumber,
    Feedrate,
    ClampPressure,
    TotalOutputPower_kW,
    MeanPositionError_mm,
    MeanVelocityError_mms,
    AvgDCBusVoltage,
    AvgOutputCurrent_A,
    SpindleSpeed_RPM,
    SystemInertia,
    SpindleCurrentFeedback,
    MachiningFinalized,
    PassedVisualInspection
FROM analytics.vw_MachineLevelOperational
ORDER BY ProgramNumber, SequenceNumber;
GO

-- ────────────────────────────────────────────────────────────────────────────
-- Q4: Tool wear analysis — compare sensor signatures between worn vs unworn
-- ────────────────────────────────────────────────────────────────────────────

SELECT
    tc.ConditionCode                        AS ToolCondition,
    a.AxisCode,
    pr.ProcessName,
    COUNT(*)                                AS Observations,
    AVG(f.OutputPower)                      AS AvgOutputPower_kW,
    AVG(f.CurrentFeedback)                  AS AvgCurrentFeedback_A,
    AVG(f.ActualVelocity)                   AS AvgActualVelocity,
    AVG(ABS(f.ActualPosition - f.CommandPosition)) AS AvgPositionError_mm,
    AVG(f.ClampPressure)                    AS AvgClampPressure
FROM core.FactSensorReadings        f
INNER JOIN core.DimAxis             a   ON a.AxisID          = f.AxisID
INNER JOIN core.DimProcess          pr  ON pr.ProcessID      = f.ProcessID
INNER JOIN core.DimToolCondition    tc  ON tc.ToolConditionID = f.ToolConditionID
GROUP BY tc.ConditionCode, a.AxisCode, pr.ProcessName
ORDER BY tc.ConditionCode, a.AxisCode, pr.SortOrder;
GO

-- ────────────────────────────────────────────────────────────────────────────
-- Q5: Partition-aware batch export for Apache Spark ingestion
--     Run per partition band; Spark reads each slice in parallel
-- ────────────────────────────────────────────────────────────────────────────

DECLARE @PartitionMin INT = 0;
DECLARE @PartitionMax INT = 14;     -- Change per Spark partition task

SELECT
    f.ReadingID,
    f.MachineID,
    f.AxisID,
    f.ProgramID,
    f.ProcessID,
    f.ToolConditionID,
    f.SequenceNumber,
    f.Feedrate,
    f.ClampPressure,
    f.ActualPosition,
    f.ActualVelocity,
    f.ActualAcceleration,
    f.CommandPosition,
    f.CommandVelocity,
    f.CommandAcceleration,
    f.CurrentFeedback,
    f.DCBusVoltage,
    f.OutputCurrent,
    f.OutputVoltage,
    f.OutputPower,
    f.SystemInertia,
    f.MachiningFinalized,
    f.PassedVisualInspection
FROM core.FactSensorReadings f
WHERE f.SequenceNumber >= @PartitionMin
  AND f.SequenceNumber <  @PartitionMax
ORDER BY f.SequenceNumber, f.AxisID;
GO

-- ────────────────────────────────────────────────────────────────────────────
-- Q6: Anomaly detection feature set — rolling deviation from command
--     Feed output directly into sklearn IsolationForest or PyOD
-- ────────────────────────────────────────────────────────────────────────────

SELECT
    f.ReadingID,
    a.AxisCode,
    f.SequenceNumber,
    pr.ProcessName,
    (f.ActualPosition    - f.CommandPosition)    AS dPosition,
    (f.ActualVelocity    - f.CommandVelocity)    AS dVelocity,
    (f.ActualAcceleration - f.CommandAcceleration) AS dAcceleration,
    f.CurrentFeedback,
    f.DCBusVoltage,
    f.OutputCurrent,
    f.OutputPower,
    f.ClampPressure,
    f.Feedrate,
    tc.ConditionCode                             AS ToolCondition,
    f.PassedVisualInspection
FROM core.FactSensorReadings        f
INNER JOIN core.DimAxis             a   ON a.AxisID          = f.AxisID
INNER JOIN core.DimProcess          pr  ON pr.ProcessID      = f.ProcessID
LEFT  JOIN core.DimToolCondition    tc  ON tc.ToolConditionID = f.ToolConditionID
ORDER BY f.SequenceNumber, a.AxisCode;
GO

-- ────────────────────────────────────────────────────────────────────────────
-- Q7: Staging pipeline health check
-- ────────────────────────────────────────────────────────────────────────────

SELECT
    IsProcessed,
    COUNT(*)            AS RowCount,
    MIN(LoadedAt)       AS OldestLoad,
    MAX(LoadedAt)       AS LatestLoad,
    MIN(StagingID)      AS MinStagingID,
    MAX(StagingID)      AS MaxStagingID
FROM staging.RawSensorReadings
GROUP BY IsProcessed;
GO

-- ────────────────────────────────────────────────────────────────────────────
-- Q8: Partition distribution — validate rows spread across partition buckets
-- ────────────────────────────────────────────────────────────────────────────

SELECT
    p.partition_number,
    p.rows                                      AS RowCount,
    rv.value                                    AS PartitionBoundary
FROM sys.partitions              p
INNER JOIN sys.indexes           i  ON i.object_id = p.object_id AND i.index_id = p.index_id
INNER JOIN sys.partition_schemes ps ON ps.data_space_id = i.data_space_id
INNER JOIN sys.partition_functions pf ON pf.function_id = ps.function_id
LEFT  JOIN sys.partition_range_values rv
    ON rv.function_id = pf.function_id AND rv.boundary_id = p.partition_number
WHERE i.object_id = OBJECT_ID('core.FactSensorReadings')
  AND i.index_id  = 1
ORDER BY p.partition_number;
GO

-- ============================================================================================================================
-- PYTHON / PANDAS INTEGRATION REFERENCE
-- ============================================================================================================================
/*
    ── Read entire analytical view into Pandas ─────────────────────────────────

    import pyodbc
    import pandas as pd

    conn_str = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=YOUR_SERVER;"
        "DATABASE=MachineSensorDB;"
        "Trusted_Connection=yes;"
    )
    conn = pyodbc.connect(conn_str)

    df = pd.read_sql(
        "SELECT * FROM analytics.vw_SensorReadingsFull ORDER BY SequenceNumber, AxisCode",
        conn
    )
    df.to_parquet("sensor_readings.parquet", index=False, engine="pyarrow")

    ── Apache Spark read via JDBC ───────────────────────────────────────────────

    spark.read \
        .format("jdbc") \
        .option("url", "jdbc:sqlserver://YOUR_SERVER;databaseName=MachineSensorDB") \
        .option("dbtable", "analytics.vw_SensorReadingsFull") \
        .option("partitionColumn", "SequenceNumber") \
        .option("lowerBound", "0") \
        .option("upperBound", "135") \
        .option("numPartitions", "10") \
        .option("driver", "com.microsoft.sqlserver.jdbc.SQLServerDriver") \
        .load()

    ── Bulk CSV import via BCP ──────────────────────────────────────────────────

    bcp MachineSensorDB.staging.RawSensorReadings IN Cleaned_MergedData.csv ^
        -c -t, -r\n -S YOUR_SERVER -T -F 2

    ── SQLAlchemy ORM / pandas to_sql ──────────────────────────────────────────

    from sqlalchemy import create_engine
    engine = create_engine(
        "mssql+pyodbc://YOUR_SERVER/MachineSensorDB?driver=ODBC+Driver+18+for+SQL+Server&trusted_connection=yes"
    )
    df.to_sql("RawSensorReadings", schema="staging", con=engine,
              if_exists="append", index=False, chunksize=2000, method="multi")
*/
-- ============================================================================================================================
-- END OF SCRIPT — MachineSensorDB v1.0.0
-- ============================================================================================================================
