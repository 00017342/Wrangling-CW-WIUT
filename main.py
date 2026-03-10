##import section
import streamlit as st
import pandas as pd

##setting the page up
st.set_page_config(layout="wide")

##data frame idk better to have it before the sidebar
df = None

##setting simple sidebar (will need change)
with st.sidebar:
    spaceLeft, mainContent, spaceRight = st.columns([0.5, 2, 0.5])

    with mainContent:
        st.header("File Upload")
        uploaded_file = st.file_uploader(
            label="Upload file",
            type=["csv", "xlsx", "xlsm", "xlsb", "xltx", "xltm", "xls"]
        )
        ##we have different functions for csv and excel... sooo i just check the extension :)
        if uploaded_file is not None:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
        
        st.write("Workflow")
        st.button("Reset Session")
        st.button("Undo Last Step")

        st.write("Logs")
        st.space(size=1)
        st.write("Here must be logs...")
        st.space(size=1)
        st.write("View full log")

##setting tabs to scroll through (will need change)
overviewTab, cleaningStudioTab, visualizationTab, exportReportTab =\
      st.tabs(["Overview", "Cleaning Studio", "Visualization", "Export & Report"],\
              width = 1490,\
              default = "Overview")

##setting overview tab (will need change)
with overviewTab:
    st.header("Dataset Overview")
    st.write("Here you can explore uploaded dataset metrics")

    ## i added rough calculation of metrics (will maybe need change too because of speed of loading)
    if df is not None:
        rows = df.shape[0]
        columns = df.shape[1]
        numeric_columns = df.select_dtypes(include="number").shape[1]
        categorical_columns = df.select_dtypes(include="object").shape[1]
        datetime_columns = df.select_dtypes(include="datetime").shape[1]
    else:
        rows = columns = numeric_columns = categorical_columns = datetime_columns = 0

    ##setting columns inside of the overview tab
    rowsColumn, columnsColumn, numericColumn, categoricalColumn, datetimeColumn = st.columns([2, 2, 2, 2, 2])

    with rowsColumn:
        st.header(rows)
        st.write("Rows")

    with columnsColumn:
        st.header(columns)
        st.write("Columns")

    with numericColumn:
        st.header(numeric_columns)
        st.write("Numeric Columns")

    with categoricalColumn:
        st.header(categorical_columns)
        st.write("Categorical Columns")

    with datetimeColumn:
        st.header(datetime_columns)
        st.write("Datetime Columns")
    
    st.space(size=20)
    
    st.header(f"Total columns: {columns}")

    st.space(size=20)

    st.header("Data Profiling")

    st.space(size=20)

    ##setting separate column field to create layout inside of overview section
    datatypesColumn, mvDPColumn = st.columns([4, 4])

    ##trying to get all types of columns, names, etc, we will think about changing it a bit and finishing that, some fields
    ##are now duplicated but we will fix it (will need change)
    with datatypesColumn:
        st.header("Data Types")

        if df is not None:
            numeric_cols = df.select_dtypes(include="number").columns
            categorical_cols = df.select_dtypes(include=["object","category"]).columns
            datetime_cols = df.select_dtypes(include=["datetime","datetimetz"]).columns

            st.write(f"Numeric columns: {len(numeric_cols)}")
            st.write(f"Categorical columns: {len(categorical_cols)}")
            st.write(f"Datetime columns: {len(datetime_cols)}")

            st.space(size=10)

            st.subheader("Column Names")

            st.write("Numeric:", ", ".join(numeric_cols) if len(numeric_cols) > 0 else "None")
            st.write("Categorical:", ", ".join(categorical_cols) if len(categorical_cols) > 0 else "None")
            st.write("Datetime:", ", ".join(datetime_cols) if len(datetime_cols) > 0 else "None")

        else:
            st.write("No dataset loaded")


    ##checking for missing values
    with mvDPColumn:
        st.header("Missing Values")

        if df is not None:
            missing_per_column = df.isnull().sum()
            total_missing = missing_per_column.sum()

            st.write(f"Total missing values: {total_missing}")

            missing_columns = missing_per_column[missing_per_column > 0]

            if len(missing_columns) == 0:
                st.write("No missing values found")
            else:
                for col, count in missing_columns.items():
                    st.write(f"{col}: {count}")
        else:
            st.write("No dataset loaded")

        st.space(size=50)

    ##checking for duplicates
    with mvDPColumn:
        st.header("Duplicates")

        if df is not None:
            duplicate_count = df.duplicated().sum()

            st.write(f"Total duplicate rows: {duplicate_count}")

            if duplicate_count > 0:
                if st.button("Remove Duplicates"):
                    df = df.drop_duplicates()
                    st.success("Duplicate rows removed")
        else:
            st.write("No dataset loaded")

##setting overview tab (will need change)
with cleaningStudioTab:
    st.header("Cleaning Studio")
    st.write("Clean, transform, and prepare your dataset with different options")

    mainColumn, metricsColumn = st. columns([4, 4])
    
    ##main columns setup (will need change)
    with mainColumn:

        with st.expander("Missing values"):
            st.header("Select columns")
            st.write("here column names")

            st.space(size=30)

            st.header("Action")
            st.write("number of missing values")
            st.button("Apply transformation")

            st.space(size=10)

            st.write("Preview: rows affected")
        
        with st.expander("Duplicate Handling"):
            st.header("Duplicate Handling")
        
        with st.expander("Data type conversion"):
            st.header("Data type conversion")
        
        with st.expander("Categorical cleaning"):
            st.header("Categorical cleaning")
        
        with st.expander("Outlier handling"):
            st.header("Outlier handling")
        
        with st.expander("Scaling"):
            st.header("Scaling")
        
        with st.expander("Column operations"):
            st.header("Column operations")
        
        with st.expander("Data validation"):
            st.header("Data validation")
    
    with metricsColumn:
        st.header("Transformation preview")
        st.write("Rows")
        st.write("Columns")
        st.write("Rows affected")
        st.write("Columns affected")
    
    with metricsColumn:
        st.header("Transformation preview")
        st.write("Information loading...")
        st.write("Information loading...")
        st.write("Information loading...")
        st.write("Information loading...")
        
        ##setting up button columns (will need change)
        buttonUndoCleaningColumn, buttonResetCleaningColumn = st.columns([2, 2])
        with buttonUndoCleaningColumn:
            st.button("Undo Last Step")
        
        with buttonResetCleaningColumn:
            st.button("Reset All")

##setting overview tab (will need change)
with visualizationTab:
    st.header("Visualization")
    st.write("Create interactive charts and explore your dataset visually")
    
    chartConfigColumn, chartOutputColumn = st.columns([1,1])
    
    with chartConfigColumn:
        containerVisualizationTab = st.container(border=True)
        with containerVisualizationTab:
            st.header("Chart Configuration")

            histColumn, boxColumn = st.columns([2,2])

            with histColumn:
                st.button("Histogram")
            
            with boxColumn:
                st.button("Box Plot")
            
            scatColumn, linecColumn = st.columns([2,2])

            with scatColumn:
                st.button("Scatter Plot")
            
            with linecColumn:
                st.button("Line Chart")

            gbarColumn, cheatColumn = st.columns([2,2])

            with gbarColumn:
                st.button("Grouped Bar Chart")
            
            with cheatColumn:
                st.button("Correlation Heatmap")
            
            st.space(size=10)

            st.header("Axes")

            st.write("X-axis")
            xaxis = st.popover("Choose")
            xaxisopt1 = xaxis.checkbox("option xaxis 1")
            xaxisopt2 = xaxis.checkbox("option xaxis 2")
            xaxisopt3 = xaxis.checkbox("option xaxis 3")

            st.write("Color/Group (Optional)")
            cgroup = st.popover("Choose")
            cgroupopt1 = cgroup.checkbox("option cgroup 1")
            cgroupopt2 = cgroup.checkbox("option cgroup 2")
            cgroupopt3 = cgroup.checkbox("option cgroup 3")

            st.write("Aggregation")
            aggreg = st.popover("Choose")
            aggregopt1 = aggreg.checkbox("option aggreg 1")
            aggregopt2 = aggreg.checkbox("option aggreg 2")
            aggregopt3 = aggreg.checkbox("option aggreg 3")

            st.space(size=10)

            st.header("Filters")

            st.write("Numeric Filter")
            numFilt = st.popover("Choose")
            numFiltopt1 = numFilt.checkbox("option numFilt 1")
            numFiltopt2 = numFilt.checkbox("option numFilt 2")
            numFiltopt3 = numFilt.checkbox("option numFilt 3")

            st.write("Categorical filter")
            catFilt = st.popover("Choose")
            catFiltopt1 = catFilt.checkbox("option catFilt 1")
            catFiltopt2 = catFilt.checkbox("option catFilt 2")
            catFiltopt3 = catFilt.checkbox("option catFilt 3")

            st.space(size=20)

            genChart, resetFilt = st.columns([2,2])
            with genChart:
                st.button("Generate Chart")

            with resetFilt:
                st.button("Reset Filters")

    with chartOutputColumn:
        containerOutputVTab = st.container(border=True)
        with containerOutputVTab:
            st.header("Visualization Output")
            
            st.space(size=30)
            st.header("HERE WILL BE VISUALIZED RESULTS")

##setting overview tab (will need change)
with exportReportTab:
    st.header("Export & Report")
    st.write("Export your cleared dataset, transformation logs and reproducible workflow recipes")

    st.space(size=35)

    st.header("Final metrics")
    finalrowsColumn, finalcolumnsColumn, transformationsColumn, validationViolationsColumn, lastChangeColumn = st.columns([2, 2, 2, 2, 2])

    with finalrowsColumn:
        st.header("Number of")
        st.write("Final Rows")

    with finalcolumnsColumn:
        st.header("Number of")
        st.write("Final Columns")

    with transformationsColumn:
        st.header("Number of")
        st.write("Transformations Applied")

    with validationViolationsColumn:
        st.header("Number of")
        st.write("Validations Violated")

    with lastChangeColumn:
        st.header("Date")
        st.write("Last Change Date")

    st.header("Export Options")

    exportColumn, transformationReportColumn = st.columns([2,2])

    with exportColumn:
        exportContainer = st.container(border=True)
        with exportContainer:
            st.header("Export Dataset")
            st.write("Download dataset in your preferred format")

            dCSVColumn, dExcelColumn = st.columns([2,2])
            with dCSVColumn:
                st.button("Download CSV")

            with dExcelColumn:
                st.button("Download Excel")
        
    with transformationReportColumn:
        transformationReportContainer = st.container(border=True)
        with transformationReportContainer:
            st.header("Transformation Report")
            st.write("Download a detailed log of all operations applied, including parameters and timestamps")
            st.button("Download report (.json)")
    
    exportWorkflowRecipeColumn, replayScriptColumn = st.columns([2,2])

    with exportWorkflowRecipeColumn:
        st.header("Export Workflow Recipe")
        st.write("Download a machine readable JSON file representing the transformation pipeline")
        st.button("Download Recipe (.json)")

    with replayScriptColumn:
        st.header("Replay Script")
        st.write("Generate a pandas based Python script that reproduces the transformation steps")

        genScriptColumn, downloadPYColumn = st.columns([2,2])
        with genScriptColumn:
            st.button("Generate script")
        
        with downloadPYColumn:
            st.button("Download .py file")
    
    transformationContainer = st.container(border=True)
    with transformationContainer:
        st.header("Transformation Log")
        st.write("Number of steps applied")

        st.space(size=30)

        st.header("HERE WILL BE LOADED LOGS")

        undoLastStepColumn, resetAllTransformationsColumn = st.columns([2,2])
        with undoLastStepColumn:
            st.button("Undo Last Applied Step")
    
        with resetAllTransformationsColumn:
            st.button("Reset All Transformations")

    recipeJSONPreviewContainer = st.container(border=True)
    with recipeJSONPreviewContainer:
        st.header("Recipe JSON Preview")