# State Machine Diagrams

This document provides comprehensive state machine diagrams for all stateful components in the Prediction Analyzer application.

## Table of Contents

1. [GUI Application State Machine](#1-gui-application-state-machine)
2. [Authentication Flow State Machine](#2-authentication-flow-state-machine)
3. [Data Fetching/Pagination State Machine](#3-data-fetchingpagination-state-machine)
4. [Filter Pipeline State Machine](#4-filter-pipeline-state-machine)
5. [PnL Calculation State Machine](#5-pnl-calculation-state-machine)
6. [Interactive CLI State Machine](#6-interactive-cli-state-machine)
7. [Chart Generation State Machine](#7-chart-generation-state-machine)
8. [Market Resolution Inference State Machine](#8-market-resolution-inference-state-machine)
9. [Export State Machine](#9-export-state-machine)

---

## 1. GUI Application State Machine

**File:** `gui.py`

The main GUI application manages the overall application state including data loading, filtering, and display.

```mermaid
stateDiagram-v2
    [*] --> NoDataLoaded: Application Start

    NoDataLoaded --> FileLoading: load_file()
    NoDataLoaded --> APIAuthenticating: load_from_api()

    FileLoading --> DataLoaded: File parsed successfully
    FileLoading --> NoDataLoaded: Parse error

    APIAuthenticating --> APIFetching: Authentication successful
    APIAuthenticating --> NoDataLoaded: Authentication failed

    APIFetching --> DataLoaded: Trades fetched
    APIFetching --> NoDataLoaded: Fetch error

    DataLoaded --> FiltersApplied: apply_filters()
    DataLoaded --> ChartGenerating: generate_chart()
    DataLoaded --> Exporting: export_data()
    DataLoaded --> FileLoading: load_file()
    DataLoaded --> APIAuthenticating: load_from_api()

    FiltersApplied --> DataLoaded: clear_filters()
    FiltersApplied --> FiltersApplied: apply_filters()
    FiltersApplied --> ChartGenerating: generate_chart()
    FiltersApplied --> Exporting: export_data()

    ChartGenerating --> DataLoaded: Chart complete
    ChartGenerating --> FiltersApplied: Chart complete (filtered)

    Exporting --> DataLoaded: Export complete
    Exporting --> FiltersApplied: Export complete (filtered)
```

### GUI State Variables

| Variable | Type | Description |
|----------|------|-------------|
| `all_trades` | `List[Trade]` | Complete trade dataset |
| `filtered_trades` | `List[Trade]` | Currently filtered subset |
| `current_file_path` | `Optional[str]` | Source file path (None for API) |
| `market_slugs` | `List[str]` | Available markets from filtered data |
| `buy_var` | `BooleanVar` | Buy filter checkbox state |
| `sell_var` | `BooleanVar` | Sell filter checkbox state |

---

## 2. Authentication Flow State Machine

**File:** `prediction_analyzer/utils/auth.py`

Handles API authentication using Ethereum private key signing.

```mermaid
stateDiagram-v2
    [*] --> Unauthenticated

    Unauthenticated --> FetchingSigningMessage: get_signing_message()

    FetchingSigningMessage --> SigningMessageReceived: API returns message
    FetchingSigningMessage --> AuthError: Network/API error

    SigningMessageReceived --> SigningMessage: Sign with private key

    SigningMessage --> PostingCredentials: authenticate()

    PostingCredentials --> Authenticated: 200 OK + session cookie
    PostingCredentials --> AuthError: 401/403/Network error

    Authenticated --> SessionActive: Cookie stored

    AuthError --> Unauthenticated: User retry

    SessionActive --> [*]: Session expires/logout
```

### Authentication State Outputs

| State | Output |
|-------|--------|
| `Unauthenticated` | No session |
| `Authenticated` | `(session_cookie, address)` tuple |
| `AuthError` | `(None, None)` tuple |

---

## 3. Data Fetching/Pagination State Machine

**File:** `prediction_analyzer/utils/data.py`

Manages paginated API data fetching with accumulation.

```mermaid
stateDiagram-v2
    [*] --> Idle

    Idle --> FetchingPage1: fetch_trade_history()

    FetchingPage1 --> ProcessingPage: Response received
    FetchingPage1 --> FetchError: Network error

    ProcessingPage --> CheckingMore: Trades accumulated

    CheckingMore --> FetchingNextPage: len(all_trades) < totalCount
    CheckingMore --> Complete: len(all_trades) >= totalCount
    CheckingMore --> Complete: Empty response

    FetchingNextPage --> ProcessingPage: Response received
    FetchingNextPage --> Complete: Network error (partial data)

    Complete --> [*]: Return all_trades
    FetchError --> [*]: Return empty list
```

### Pagination State Variables

| Variable | Type | Description |
|----------|------|-------------|
| `all_trades` | `List[dict]` | Accumulating trades |
| `page` | `int` | Current page number |
| `total_count` | `int` | Total available from API |

---

## 4. Filter Pipeline State Machine

**File:** `prediction_analyzer/filters.py`

Sequential filter application with validation.

```mermaid
stateDiagram-v2
    [*] --> Unfiltered: Input trades

    Unfiltered --> ValidatingDateInputs: Date filter requested

    ValidatingDateInputs --> DateFiltering: Valid format
    ValidatingDateInputs --> ValidationError: Invalid format

    DateFiltering --> DateFiltered: Apply filter_by_date()

    DateFiltered --> TypeFiltering: Type filter requested
    DateFiltered --> PnLFiltering: PnL filter requested
    DateFiltered --> Complete: No more filters

    TypeFiltering --> TypeFiltered: Apply filter_by_trade_type()

    TypeFiltered --> PnLFiltering: PnL filter requested
    TypeFiltered --> Complete: No more filters

    ValidatingPnLInputs --> PnLFiltering: Valid numeric
    ValidatingPnLInputs --> ValidationError: Invalid format

    PnLFiltering --> PnLFiltered: Apply filter_by_pnl()

    PnLFiltered --> Complete: All filters applied

    ValidationError --> Unfiltered: Show error message

    Complete --> [*]: Return filtered_trades
```

### Filter Functions (Pure State Transformers)

```
Input State: List[Trade]
    │
    ├── filter_by_date(start, end)     → List[Trade]
    │
    ├── filter_by_trade_type(types)    → List[Trade]
    │
    ├── filter_by_side(sides)          → List[Trade]
    │
    └── filter_by_pnl(min, max)        → List[Trade]

Output State: List[Trade] (subset)
```

---

## 5. PnL Calculation State Machine

**File:** `prediction_analyzer/pnl.py`

Cumulative PnL calculation with running totals.

```mermaid
stateDiagram-v2
    [*] --> Initialize: calculate_pnl(trades)

    Initialize --> SortTrades: Set cumulative = 0

    SortTrades --> ProcessingTrade: Sort by timestamp

    ProcessingTrade --> CalculatingCost: Get next trade

    CalculatingCost --> UpdatingCumulative: Determine buy/sell

    UpdatingCumulative --> UpdatingExposure: cumulative += pnl

    UpdatingExposure --> ProcessingTrade: More trades
    UpdatingExposure --> Summarizing: No more trades

    Summarizing --> Complete: Calculate final metrics

    Complete --> [*]: Return summary dict
```

### PnL State Accumulation

```mermaid
stateDiagram-v2
    direction LR

    state "Trade Processing Loop" as loop {
        [*] --> ReadTrade
        ReadTrade --> IsBuy: Check type
        ReadTrade --> IsSell: Check type

        IsBuy --> UpdateExposure: exposure += cost
        IsSell --> UpdateExposure: exposure -= cost

        UpdateExposure --> UpdateShares: Update position
        UpdateShares --> UpdatePnL: Calculate P&L
        UpdatePnL --> [*]: Next trade
    }
```

### Summary State Output

| Metric | Calculation |
|--------|-------------|
| `total_pnl` | Sum of all trade PnLs |
| `winning_trades` | Count where pnl > 0 |
| `losing_trades` | Count where pnl < 0 |
| `win_rate` | winning / total * 100 |
| `roi` | total_pnl / total_invested * 100 |

---

## 6. Interactive CLI State Machine

**File:** `prediction_analyzer/core/interactive.py`

Menu-driven CLI navigation system.

```mermaid
stateDiagram-v2
    [*] --> MainMenu: interactive_menu()

    MainMenu --> GlobalSummary: Choice "1"
    MainMenu --> MarketSelection: Choice "2"
    MainMenu --> ExportMenu: Choice "3"
    MainMenu --> FullReport: Choice "4"
    MainMenu --> [*]: Choice "Q"

    GlobalSummary --> WaitingForEnter: Display summary
    WaitingForEnter --> MainMenu: Enter pressed

    MarketSelection --> DisplayingMarkets: Load markets
    DisplayingMarkets --> FilterMenu: Market selected
    DisplayingMarkets --> MainMenu: "B" (Back)

    FilterMenu --> ApplyingDateFilter: Choice "1"
    FilterMenu --> ApplyingTypeFilter: Choice "2"
    FilterMenu --> ApplyingPnLFilter: Choice "3"
    FilterMenu --> FilterMenu: Choice "4" (Clear)
    FilterMenu --> ChartSelection: Choice "5" (Done)

    ApplyingDateFilter --> FilterMenu: Filter applied
    ApplyingTypeFilter --> FilterMenu: Filter applied
    ApplyingPnLFilter --> FilterMenu: Filter applied

    ChartSelection --> GeneratingChart: Chart type selected
    GeneratingChart --> MainMenu: Chart complete

    ExportMenu --> ExportingCSV: Choice "1"
    ExportMenu --> ExportingExcel: Choice "2"
    ExportMenu --> MainMenu: Choice "3" (Back)

    ExportingCSV --> WaitingForEnter2: File written
    ExportingExcel --> WaitingForEnter2: File written
    WaitingForEnter2 --> MainMenu: Enter pressed

    FullReport --> WaitingForEnter3: Report generated
    WaitingForEnter3 --> MainMenu: Enter pressed
```

### Menu State Hierarchy

```
MainMenu
├── [1] GlobalSummary → Display → Return
├── [2] MarketSelection
│   └── FilterMenu
│       ├── [1] DateFilter → Apply → Return to FilterMenu
│       ├── [2] TypeFilter → Apply → Return to FilterMenu
│       ├── [3] PnLFilter → Apply → Return to FilterMenu
│       ├── [4] ClearFilters → Return to FilterMenu
│       └── [5] Done → ChartSelection → Generate → Return to Main
├── [3] ExportMenu
│   ├── [1] CSV Export → Write → Return
│   ├── [2] Excel Export → Write → Return
│   └── [3] Back → Return to Main
├── [4] FullReport → Generate → Return
└── [Q] Quit → Exit
```

---

## 7. Chart Generation State Machine

**Files:** `prediction_analyzer/charts/*.py`

Stateful chart generation with cumulative calculations.

```mermaid
stateDiagram-v2
    [*] --> Initialize: generate_*_chart()

    Initialize --> SortingTrades: Receive trades list

    SortingTrades --> InitializingMetrics: Sort by timestamp

    InitializingMetrics --> ProcessingTrade: Set net_exposure = 0

    state "Trade Loop" as loop {
        ProcessingTrade --> CalculatingPosition: Read trade
        CalculatingPosition --> UpdatingExposure: Update shares
        UpdatingExposure --> CalculatingPnL: Update cash
        CalculatingPnL --> RecordingDataPoint: Calculate mark-to-market
        RecordingDataPoint --> ProcessingTrade: More trades
    }

    RecordingDataPoint --> BuildingFigure: All trades processed

    BuildingFigure --> AddingTraces: Create plot
    AddingTraces --> AddingAnnotations: Add data series
    AddingAnnotations --> SavingFile: Add labels

    SavingFile --> LaunchingBrowser: Write HTML/PNG
    SavingFile --> Complete: No browser launch

    LaunchingBrowser --> Complete: Browser opened

    Complete --> [*]: Return
```

### Chart Type State Variants

| Chart Type | File | Key State Variables |
|------------|------|---------------------|
| Simple | `simple.py` | `net_exposure`, `exposures[]`, `final_pnl` |
| Pro | `pro.py` | `cumulative_pnl`, `net_exposure`, `colors[]` |
| Enhanced | `enhanced.py` | `current_shares`, `current_cost`, `running_pnl` |
| Dashboard | `global_chart.py` | `per_market_pnl`, `total_portfolio_pnl` |

---

## 8. Market Resolution Inference State Machine

**File:** `prediction_analyzer/inference.py`

Determines market outcome from trade patterns.

```mermaid
stateDiagram-v2
    [*] --> AnalyzingTrades: infer_resolved_side()

    AnalyzingTrades --> FindingLatestTrade: Sort by timestamp

    FindingLatestTrade --> CheckingPrice: Get last trade

    CheckingPrice --> InferYES: price >= 0.50 (50¢)
    CheckingPrice --> InferOpposite: price < 0.50

    InferYES --> Resolved: Return "YES"

    InferOpposite --> CheckingSide: Get trade side
    CheckingSide --> ResolvedNO: side == "YES"
    CheckingSide --> ResolvedYES: side == "NO"

    ResolvedYES --> Resolved: Return "YES"
    ResolvedNO --> Resolved: Return "NO"

    Resolved --> [*]: Return (inferred_side, latest_trade)
```

### Inference Logic

```
IF latest_price >= $0.50:
    inferred_outcome = "YES"  # High price = market resolved YES
ELSE:
    IF latest_side == "YES":
        inferred_outcome = "NO"   # Bought YES cheap = market went NO
    ELSE:
        inferred_outcome = "YES"  # Bought NO cheap = market went YES
```

---

## 9. Export State Machine

**File:** `prediction_analyzer/reporting/report_data.py`

File export workflow with format selection.

```mermaid
stateDiagram-v2
    [*] --> SelectingFormat: export_data()

    SelectingFormat --> GeneratingFilename: Format chosen

    GeneratingFilename --> ShowingSaveDialog: Create default name

    ShowingSaveDialog --> PreparingData: Path confirmed
    ShowingSaveDialog --> Cancelled: User cancelled

    PreparingData --> WritingCSV: CSV format
    PreparingData --> WritingExcel: Excel format

    WritingCSV --> Success: File written
    WritingCSV --> ExportError: IO error

    WritingExcel --> Success: File written
    WritingExcel --> ExportError: IO error

    Success --> ShowingConfirmation: Display path
    ExportError --> ShowingError: Display message

    ShowingConfirmation --> [*]
    ShowingError --> [*]
    Cancelled --> [*]
```

---

## Component State Summary

| Component | State Type | Persistence | Side Effects |
|-----------|-----------|-------------|--------------|
| GUI | Class instance | Session | UI updates, file I/O |
| Auth | Transient | HTTP cookie | Network requests |
| Data Fetch | Transient | None | Network requests |
| Filters | Pure functional | None | None |
| PnL | Transient | None | Calculations only |
| Interactive CLI | Loop-based | Session | Console I/O |
| Charts | Transient | File output | File I/O, browser |
| Inference | Pure functional | None | None |
| Export | Transient | File output | File I/O |

---

## State Flow Overview

```mermaid
flowchart TB
    subgraph "Data Acquisition"
        A[Start] --> B{Load Source}
        B -->|File| C[FileLoader]
        B -->|API| D[Authentication]
        D --> E[DataFetcher]
        C --> F[Trade Objects]
        E --> F
    end

    subgraph "Data Processing"
        F --> G[Filter Pipeline]
        G --> H[Filtered Trades]
        H --> I[PnL Calculator]
        I --> J[Summary Stats]
    end

    subgraph "Output Generation"
        H --> K{Output Type}
        K -->|Chart| L[Chart Generator]
        K -->|Report| M[Report Generator]
        K -->|Export| N[File Exporter]
        L --> O[Visual Output]
        M --> P[Text Output]
        N --> Q[File Output]
    end
```

---

## Appendix: State Transition Triggers

### User Actions
| Trigger | Component | Transition |
|---------|-----------|------------|
| Click "Load File" | GUI | NoDataLoaded → FileLoading |
| Click "Load from API" | GUI | NoDataLoaded → APIAuthenticating |
| Click "Apply Filters" | GUI | DataLoaded → FiltersApplied |
| Click "Clear Filters" | GUI | FiltersApplied → DataLoaded |
| Select menu option | CLI | CurrentMenu → SelectedSubmenu |

### System Events
| Event | Component | Transition |
|-------|-----------|------------|
| HTTP 200 response | Auth | PostingCredentials → Authenticated |
| HTTP error | Auth | PostingCredentials → AuthError |
| Last page fetched | DataFetch | CheckingMore → Complete |
| File write success | Export | WritingFile → Success |

### Data Events
| Event | Component | Transition |
|-------|-----------|------------|
| Trade processed | PnL | ProcessingTrade → UpdatingCumulative |
| All trades done | Chart | RecordingDataPoint → BuildingFigure |
| Filter applied | Filter | Input → Output (pure transform) |
