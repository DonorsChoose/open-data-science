import pandas as pd

# Needs to be changed later?
def subset_df_by_id(df, ids = []):
    """Get subset of resources DataFrame based on list of project IDs."""
    return df[df["Project ID"].isin(ids)]

def resource_formatter(resource_path):
    print("Reading in resource data...")
    resources = pd.read_csv(resource_path)
    resources.columns = ["Project ID", "Project Posted Date", "Cleaned Item Name"]
    resources_list = list(resources["Cleaned Item Name"])
    resources_list = [str(x).split() for x in resources_list]
    resources["Cleaned Item Name"] = resources_list
    print("Consolidating resources per project for "+str(resources["Project ID"].nunique())+" projects ...")
    consolidated = pd.DataFrame(resources.groupby(["Project Posted Date", "Project ID"])["Cleaned Item Name"].sum())
    consolidated.reset_index(inplace=True)
    del resources # For memory
    print("Resources read and formatted!")
    
    return consolidated

def project_formatter(project_path):
    print("Reading in project data...")
    projects = pd.read_csv(project_path)
    projects["Project Posted Date"] = pd.to_datetime(projects["Project Posted Date"])
    print("Projects read and formatted!")
    
    return projects

def format_current_trends(current_trends):
    # Get subset of columns to display as main page of application
    current_trends_table = current_trends[["Rank", "word", "weight", "prop", "historical_mean"]]
    # Rename columns for display
    current_trends_table.columns = ["Rank", "Keyword", "Weight", "Current Proportion", "Historical Proportion"]
    # Format numbers for display
    for col in current_trends_table.columns:
        if "Proportion" in col:
            # convert to proportion
            current_trends_table[col] = current_trends_table[col].apply(lambda x: "{:.2%}".format(x))
        if col is "Weight":
            # round
            current_trends_table[col] = current_trends_table[col].apply(lambda x: "{:.2f}".format(x))
            
    return current_trends_table