import pandas as pd
import jsonlines
import json
import re
import sqlite3
import sys
import Levenshtein

def db_loader(target_ehr):
    ehr_dict = {"admissions":"./ehrsql-ehragent/mimic_iii/ADMISSIONS.csv",
                "chartevents":"./ehrsql-ehragent/mimic_iii/CHARTEVENTS.csv",
                "cost":"./ehrsql-ehragent/mimic_iii/COST.csv",
                "d_icd_diagnoses":"./ehrsql-ehragent/mimic_iii/D_ICD_DIAGNOSES.csv",
                "d_icd_procedures":"./ehrsql-ehragent/mimic_iii/D_ICD_PROCEDURES.csv",
                "d_items":"./ehrsql-ehragent/mimic_iii/D_ITEMS.csv",
                "d_labitems":"./ehrsql-ehragent/mimic_iii/D_LABITEMS.csv",
                "diagnoses_icd":"./ehrsql-ehragent/mimic_iii/DIAGNOSES_ICD.csv",
                "icustays":"./ehrsql-ehragent/mimic_iii/ICUSTAYS.csv",
                "inputevents_cv":"./ehrsql-ehragent/mimic_iii/INPUTEVENTS_CV.csv",
                "labevents":"./ehrsql-ehragent/mimic_iii/LABEVENTS.csv",
                "microbiologyevents":"./ehrsql-ehragent/mimic_iii/MICROBIOLOGYEVENTS.csv",
                "outputevents":"<YOUR_DATASET_PATH>/mimic_iii/OUTPUTEVENTS.csv",
                "patients":"./ehrsql-ehragent/mimic_iii/PATIENTS.csv",
                "prescriptions":"./ehrsql-ehragent/mimic_iii/PRESCRIPTIONS.csv",
                "procedures_icd":"./ehrsql-ehragent/mimic_iii/PROCEDURES_ICD.csv",
                "transfers":"./ehrsql-ehragent/mimic_iii/TRANSFERS.csv",
                }
    data = pd.read_csv(ehr_dict[target_ehr])
    # data = data.astype(str)
    column_names = ', '.join(data.columns.tolist())
    return data
# def get_column_names(self, target_db):
#     return ', '.join(data.columns.tolist())

def data_filter(data, argument):
    # commands = re.sub(r' ', '', argument)
    backup_data = data
    # print('-->', argument)
    commands = argument.split('||')
    for i in range(len(commands)):
        try:
            # commands[i] = commands[i].replace(' ', '')
            if '>=' in commands[i]:
                command = commands[i].split('>=')
                column_name = command[0]
                value = command[1]
                try:
                    value = type(data[column_name][0])(value)
                except:
                    value = value
                data = data[data[column_name] >= value]
            elif '<=' in commands[i]:
                command = commands[i].split('<=')
                column_name = command[0]
                value = command[1]
                try:
                    value = type(data[column_name][0])(value)
                except:
                    value = value
                data = data[data[column_name] <= value]
            elif '>' in commands[i]:
                command = commands[i].split('>')
                column_name = command[0]
                value = command[1]
                try:
                    value = type(data[column_name][0])(value)
                except:
                    value = value
                data = data[data[column_name] > value]
            elif '<' in commands[i]:
                command = commands[i].split('<')
                column_name = command[0]
                value = command[1]
                if value[0] == "'" or value[0] == '"':
                    value = value[1:-1]
                try:
                    value = type(data[column_name][0])(value)
                except:
                    value = value
                data = data[data[column_name] < value]
            elif '=' in commands[i]:
                command = commands[i].split('=')
                column_name = command[0]
                value = command[1]
                
                # Remove spaces and handle possible quotations around values
                value_list = [v.strip().strip("'").strip('"') for v in value.split(',')]
                
                # Try converting each value to match the type of the column values
                try:
                    # Check the type of the first value in the column
                    examplar = backup_data[column_name].tolist()[0]
                    value_list = [type(examplar)(v) for v in value_list]
                except:
                    # If conversion fails, leave the values as strings
                    pass
                
                # Filter the data to include rows where the column's value is in the provided list
                data = data[data[column_name].isin(value_list)]
            elif ' in ' in commands[i]:
                command = commands[i].split(' in ')
                column_name = command[0]
                value = command[1]
                value_list = [s.strip() for s in value.strip("[]").split(',')]
                value_list = [s.strip("'").strip('"') for s in value_list]
                # print(command)
                # print(column_name)
                # print(value)
                # print(value_list)
                value_list = list(map(type(data[column_name][0]), value_list))
                # print(len(data))
                data = data[data[column_name].isin(value_list)]
                # print(len(data))
            elif 'max' in commands[i]:
                command = commands[i].split('max(')
                column_name = command[1].split(')')[0]
                data = data[data[column_name] == data[column_name].max()]
            elif 'min' in commands[i]:
                command = commands[i].split('min(')
                column_name = command[1].split(')')[0]
                data = data[data[column_name] == data[column_name].min()]
        except:
            if column_name not in data.columns.tolist():
                columns = ', '.join(data.columns.tolist())
                raise Exception("The filtering query {} is incorrect. Please modify the column name or use LoadDB to read another table. The column names in the current DB are {}.".format(commands[i], columns))
            if column_name == '' or value == '':
                raise Exception("The filtering query {} is incorrect. There is syntax error in the command. Please modify the condition or use LoadDB to read another table.".format(commands[i]))
        if len(data) == 0:
            # get 5 examples from the backup data what is in the same column
            column_values = list(set(backup_data[column_name].tolist()))
            if ('=' in commands[i]) and (not value in column_values) and (not '>=' in commands[i]) and (not '<=' in commands[i]):
                levenshtein_dist = {}
                for cv in column_values:
                    levenshtein_dist[cv] = Levenshtein.distance(str(cv), str(value))
                levenshtein_dist = sorted(levenshtein_dist.items(), key=lambda x: x[1], reverse=False)
                column_values = [i[0] for i in levenshtein_dist[:5]]
                column_values = ', '.join([str(i) for i in column_values])
                raise Exception("The filtering query {} is incorrect. There is no {} value in the column. Five example values in the column are {}. Please check if you get the correct {} value.".format(commands[i], value, column_values, column_name))
            else:
                return data
    return data

def get_value(data, argument):
    try:
        commands = argument.split(', ')
        if len(commands) == 1:
            column = argument
            while column[0] == '[' or column[0] == "'":
                column = column[1:]
            while column[-1] == ']' or column[-1] == "'":
                column = column[:-1]
            if len(data) == 1:
                return str(data.iloc[0][column])
            else:
                answer_list = list(set(data[column].tolist()))
                answer_list = [str(i) for i in answer_list]
                return ', '.join(answer_list)
                # else:
                #     return "Get the value. But there are too many returned values. Please double-check the code and make necessary changes."
        else:
            column = commands[0]
            if 'mean' in commands[-1]:
                res_list = data[column].tolist()
                res_list = [float(i) for i in res_list]
                return sum(res_list)/len(res_list)
            elif 'max' in commands[-1]:
                res_list = data[column].tolist()
                try:
                    res_list = [float(i) for i in res_list]
                except:
                    res_list = [str(i) for i in res_list]
                return max(res_list)
            elif 'min' in commands[-1]:
                res_list = data[column].tolist()
                try:
                    res_list = [float(i) for i in res_list]
                except:
                    res_list = [str(i) for i in res_list]
                return min(res_list)
            elif 'sum' in commands[-1]:
                res_list = data[column].tolist()
                res_list = [float(i) for i in res_list]
                return sum(res_list)
            elif 'list' in commands[-1]:
                res_list = data[column].tolist()
                res_list = [str(i) for i in res_list]
                return ', '.join(list(res_list))
            else:
                raise Exception("The operation {} contains syntax errors. Please check the arguments.".format(commands[-1]))
    except:
        column_values = ', '.join(data.columns.tolist())
        raise Exception("The column name {} is incorrect. Please check the column name and make necessary changes. The columns in this table include {}.".format(column, column_values))

def sql_interpreter(command):
    con = sqlite3.connect("./ehrsql-ehragent/mimic_iii/mimic_iii.db")
    cur = con.cursor()
    results = cur.execute(command).fetchall()
    return results

def date_calculator(argument):
    try:
        con = sqlite3.connect("./ehrsql-ehragent/mimic_iii/mimic_iii.db")
        cur = con.cursor()
        command = "select datetime(current_time, '{}')".format(argument)
        results = cur.execute(command).fetchall()[0][0]
    except:
        raise Exception("The date calculator {} is incorrect. Please check the syntax and make necessary changes. For the current date and time, please call Calendar('0 year').".format(argument))
    return results

# if __name__ == "__main__":
#     db = table_toolkits()
#     print(db.db_loader("microbiologyevents"))
#     # print(db.data_filter("SPEC_TYPE_DESC=peripheral blood lymphocytes"))
#     print(db.data_filter("HADM_ID=107655"))
#     print(db.data_filter("SPEC_TYPE_DESC=peripheral blood lymphocytes"))
#     print(db.get_value('CHARTTIME'))
#     # results = db.sql_interpreter("select max(t1.c1) from ( select sum(cost.cost) as c1 from cost where cost.hadm_id in ( select diagnoses_icd.hadm_id from diagnoses_icd where diagnoses_icd.icd9_code = ( select d_icd_diagnoses.icd9_code from d_icd_diagnoses where d_icd_diagnoses.short_title = 'comp-oth vasc dev/graft' ) ) and datetime(cost.chargetime) >= datetime(current_time,'-1 year') group by cost.hadm_id ) as t1")
#     # results = [result[0] for result in results]
#     # if len(results) == 1:
#     #     print(results[0])
#     # else:
#     #     print(results)
#     # print(db.date_calculator('-1 year'))

if __name__ == "__main__":
    # data = db_loader("microbiologyevents")
    # print(data)
    # print(data_filter(data, "HADM_ID=107655"))
    # print(data_filter(data, "SPEC_TYPE_DESC=peripheral blood lymphocytes"))
    # print(get_value(data, 'CHARTTIME'))
    # date = date_calculator('-1 year')
    # patient_db = db_loader('admissions')
    # filtered_patient_db = data_filter(patient_db, 'SUBJECT_ID=9474')
    # hadm_id = get_value(filtered_patient_db, 'HADM_ID')
    # print(hadm_id, date)
    # diagnoses_icd_db = db_loader('diagnoses_icd')
    # filtered_diagnoses_icd_db = data_filter(diagnoses_icd_db, 'HADM_ID={}||CHARTTIME>{}'.format(hadm_id, date))
    # if len(filtered_diagnoses_icd_db) > 0:
    #     icd_code = get_value(filtered_diagnoses_icd_db, 'ICD9_CODE')
    #     if icd_code:
    #         d_icd_diagnoses_db = db_loader('d_icd_diagnoses')
    #         filtered_d_icd_diagnoses_db = data_filter(d_icd_diagnoses_db, 'ICD9_CODE={}'.format(icd_code))
    #         if len(filtered_d_icd_diagnoses_db) > 0:
    #             diagnosis_name = get_value(filtered_d_icd_diagnoses_db, 'SHORT_TITLE')
    #             answer = 1    
    #         else:
    #              answer = 0
    #     else:
    #         answer = 0
    # else:
    #     answer = 0
    # print(answer)

    date = date_calculator('-1 year')
    # We can find the visiting information of patient 9474 in the admissions database to determine their hospital stays
    admissions_db = db_loader('admissions')
    filtered_admissions_db = data_filter(admissions_db, 'SUBJECT_ID=9474')
    hadm_id_list = get_value(filtered_admissions_db, 'HADM_ID, list')
    # Initialize answer to 0 (no diagnosis found)
    answer = 0
    # Check if hadm_id_list is not empty before proceeding
    if hadm_id_list:    
        # We will check the diagnoses_icd database to see if there are any records of diagnoses associated with the HADM_IDs from the admissions database for the past year.   
        diagnoses_icd_db = db_loader('diagnoses_icd')
        filtered_diagnoses_icd_db = data_filter(diagnoses_icd_db, 'HADM_ID in ({})'.format(','.join(hadm_id_list)))
        # The diagnoses will be linked to the corresponding ICD9_CODE, which can be cross-referenced with the d_icd_diagnoses database to obtain the details of the diagnoses received by patient 9474.
        if len(filtered_diagnoses_icd_db) > 0:
            answer = 1
    print(answer)
                    