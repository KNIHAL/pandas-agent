# Pandas Data Cleaning Agent

An intelligent AI-powered data cleaning agent built with CrewAI and Pandas MCP Server integration. This agent automatically loads, cleans, analyzes, and saves datasets from various formats including CSV, Excel, JSON, and SQL databases.

## 🌟 Features

- 🤖 **AI-Powered Cleaning**: Uses Google Gemini 2.0 Flash for intelligent data cleaning decisions
- 📁 **Multiple Format Support**: Works with CSV, Excel (XLSX/XLS), JSON, and SQL databases
- 🧹 **Automatic Cleaning**: Removes nulls, duplicates, and handles outliers
- 💬 **Interactive Queries**: Ask questions about your data during the cleaning process
- 💾 **Auto-Save**: Automatically saves cleaned data in a `cleaned/` folder
- 🔧 **MCP Integration**: Leverages Pandas MCP Server tools for robust data operations

## 📋 Prerequisites

- Python 3.12 or higher
- Google Gemini API key
- Pandas MCP Server (included in this project)

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/KNIHAL/pandas-agent.git
cd pandas-agent
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup Environment Variables

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your_gemini_api_key_here
```

Or the agent will prompt you to enter the API key when you run it.

### 4. Verify MCP Server

Ensure `server.py` (Pandas MCP Server) is in the same directory as `agent.py`.

## 🎯 How It Works

### Architecture

```
User Input → CrewAI Agent → Pandas MCP Server → Data Processing → Cleaned Output
```

1. **User provides file path** (CSV, Excel, JSON, or SQL connection)
2. **Agent loads data** using MCP tools
3. **Agent analyzes** and identifies data quality issues
4. **Agent cleans data**:
   - Removes null/missing values
   - Eliminates duplicate rows
   - Handles outliers
5. **Agent answers queries** about the dataset
6. **Agent saves cleaned data** to `cleaned/` folder

### Agent Configuration

**Role**: Data Cleaning Agent  
**Goal**: Load, clean, analyze, and save datasets  
**Capabilities**:
- Read CSV, Excel, JSON files
- Connect to SQL databases
- Remove nulls and duplicates
- Handle outliers intelligently
- Answer data-related queries
- Save cleaned datasets

**LLM**: Google Gemini 2.0 Flash (Temperature: 0.1 for consistent results)

## 💻 Usage

### Basic Usage

```bash
python agent.py
```

The agent will prompt you:
```
Enter path to your data file (CSV / Excel):
```

### Example Workflows

#### 1. Clean a CSV File

```bash
python agent.py
# Input: /path/to/sales_data.csv
```

**Agent will:**
- Load the CSV file
- Identify and remove null values
- Remove duplicate rows
- Detect and handle outliers
- Save cleaned file to `cleaned/sales_data_cleaned.csv`

#### 2. Clean an Excel File

```bash
python agent.py
# Input: /path/to/customer_data.xlsx
```

**Agent handles:**
- Multiple sheets (if present)
- Mixed data types
- Date formatting issues
- Missing values

#### 3. Clean JSON Data

```bash
python agent.py
# Input: /path/to/transactions.json
```

**Agent processes:**
- Nested JSON structures
- Array data
- Type conversions

#### 4. Query SQL Database

```bash
python agent.py
# Input: sqlite:///mydata.db
# (You can also provide specific SQL queries)
```

## 🔧 Advanced Configuration

### Customize Agent Behavior

Edit `agent.py` to modify agent parameters:

```python
pandas_agent = Agent(
    role="Data Cleaning Agent",
    goal="Your custom goal here",
    backstory="Your custom backstory",
    tools=tools,
    reasoning=True,           # Enable reasoning mode
    verbose=True,            # Show detailed logs
    allow_code_execution=True,  # Allow pandas code execution
)
```

### Modify Cleaning Task

```python
processing_task = Task(
    description="Your custom cleaning workflow",
    expected_output="Expected output format",
    agent=pandas_agent,
    markdown=True,
)
```

### Change LLM Model

```python
llm = LLM(
    api_key=os.getenv("GOOGLE_API_KEY"),
    model="gemini/gemini-2.0-flash",  # or "gemini/gemini-pro"
    temperature=0.1,  # Adjust for creativity vs consistency
)
```

## 📊 Output

The agent provides a structured markdown response including:

### Cleaning Summary
- Number of null values removed
- Number of duplicate rows eliminated
- Outlier treatment details
- Data type conversions performed

### File Information
- Path to cleaned file
- File format and size
- Number of rows and columns
- Column names and types

### Query Answers
- Responses to any questions asked during cleaning
- Statistical summaries
- Data insights

## 🛠️ MCP Tools Used

The agent has access to all Pandas MCP Server tools:

1. **read_metadata_tool**: Analyze file structure
2. **run_pandas_code_tool**: Execute pandas operations
3. **read_json_tool**: Load JSON files
4. **dataframe_to_json_tool**: Save to JSON
5. **read_sql_tool**: Query databases
6. **dataframe_to_sql_tool**: Save to database
7. **generate_chartjs_tool**: Create visualizations

## 📁 Project Structure

```
pandas-data-cleaning-agent/
│
├── agent.py              # Main CrewAI agent
├── server.py             # Pandas MCP Server
├── core/                 # MCP Server core modules
│   ├── config.py
│   ├── metadata.py
│   ├── execution.py
│   └── visualization.py
├── cleaned/              # Output folder (auto-created)
├── .env                  # Environment variables
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## 🔒 Security

- **Code Execution Safety**: MCP Server blocks dangerous operations (os, sys, exec, eval)
- **Input Validation**: File paths and SQL queries are validated
- **API Key Protection**: API keys stored in `.env` file (never commit to git)

## 🐛 Troubleshooting

### Common Issues

**1. "Module not found" error**
```bash
pip install crewai crewai-tools python-dotenv
```

**2. "MCP Server not found"**
- Ensure `server.py` is in the same directory as `agent.py`
- Check file permissions: `chmod +x server.py`

**3. "API key invalid"**
- Verify your Google Gemini API key in `.env`
- Get a new key from: https://makersuite.google.com/app/apikey

**4. "File not found" error**
- Use absolute paths: `/full/path/to/file.csv`
- Check file permissions and existence

**5. "Python version mismatch"**
- Ensure Python 3.12+ is installed
- Update `UV_PYTHON` in `agent.py` if needed

## 🎓 Examples

### Example 1: Sales Data Cleaning

**Input**: `sales_2024.csv` with 10,000 rows, 15 columns  
**Issues**: 500 null values, 120 duplicates, pricing outliers

**Agent Actions**:
1. Loaded CSV file
2. Removed 500 rows with critical nulls
3. Eliminated 120 duplicate transactions
4. Capped price outliers at 99th percentile
5. Saved cleaned file with 9,380 rows

**Output**: `cleaned/sales_2024_cleaned.csv`

### Example 2: Customer Database

**Input**: Excel file with multiple sheets  
**Issues**: Mixed data types, date format inconsistencies

**Agent Actions**:
1. Processed all sheets
2. Standardized date formats
3. Converted string numbers to numeric
4. Merged clean data
5. Saved as unified CSV

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details

## 🙏 Acknowledgments

- **CrewAI**: For the amazing agent framework
- **Pandas MCP Server**: For robust data handling tools
- **Google Gemini**: For powerful AI capabilities

## 📞 Support

For issues or questions:
- Open an issue on GitHub
- Check existing issues and discussions

## 🔄 Changelog

### Version 1.0.0
- ✅ Initial release
- ✅ CSV, Excel, JSON, SQL support
- ✅ Automatic cleaning (nulls, duplicates, outliers)
- ✅ Interactive query support
- ✅ Auto-save functionality
- ✅ Google Gemini 2.0 Flash integration
- ✅ CrewAI agent implementation
- ✅ Pandas MCP Server integration

## 🚀 Roadmap

- [ ] Add data visualization dashboard
- [ ] Support for more file formats (Parquet, Avro)
- [ ] Custom cleaning rules configuration
- [ ] Multi-agent collaboration for complex datasets
- [ ] Web UI for easier interaction
- [ ] Scheduled cleaning jobs
- [ ] Data quality scoring system

---

**Made with ❤️ using CrewAI and Pandas MCP Server**
