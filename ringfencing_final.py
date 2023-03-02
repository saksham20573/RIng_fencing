# -*- coding: utf-8 -*-
"""Ringfencing_final.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1vrzC_QK0eItCI4C9V1eb7GGEmdQnmfcr
"""

# Some of the code provided in this implementation has been incorporated into the model https://aneesha.medium.com/natural-language-queries-for-any-database-table-with-zero-shot-roberta-based-sql-query-generation-51df57c449e2

# Install libs
!pip install tableschema
!pip install sqlalchemy
!pip install records
!pip install transformers
!pip install sentence-transformers

# Commented out IPython magic to ensure Python compatibility.
# Imports
import csv
from tableschema import infer
import io
import pandas as pd
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String
from google.colab import files
from google.colab import data_table
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from sklearn import preprocessing
from sklearn.svm import SVC
from datetime import date
from transformers import BertTokenizer, BertForTokenClassification, pipeline

from nltk.tokenize import word_tokenize
import unicodedata
import spacy
from difflib import SequenceMatcher
# from ner import Parser

from sklearn.linear_model import LogisticRegression

# Load Google Collab Extensions
# %load_ext google.colab.data_table

!python -m spacy download en_core_web_trf

!pip install spacy-transformers

# Upload the sample schema file
uploaded = files.upload()

# Path to dataset
df = pd.read_csv("/content/drive/MyDrive/Final Ring fencing dataset - Sheet1.csv")

"""#Evaluate"""

def get_feature_model2(data_frame):
  """
  Input a data frame and return the embedding vectors for the each sentence column using model2,
  Return 2 matrices each of shape (#_samples, #size_of_word_emb).
  """
# sentence-transformers/all-distilroberta-v1
  non_cont_model2 = SentenceTransformer('distilbert-base-uncased')
  
  feature1 = non_cont_model2.encode(data_frame)
  
  return feature1

def classify_query(Query):
  df = pd.read_csv("/content/drive/MyDrive/Final Ring fencing dataset - Sheet1.csv")
  column = "LABEL"
  df_enc = df.copy()
  for i in df_enc.index:
    if df[column][i] == "WITHDRAW":
        df_enc[column][i] = 0
    elif df[column][i] == "DEPOSIT":
        df_enc[column][i] = 1
    else:
        df_enc[column][i] = 2

  df_enc = df_enc.sample(frac = 1)
  X = df_enc["ENTRY"]
  y = df_enc["LABEL"]
  y=y.astype('int')
  # X_train, X_test, y_train, y_test = train_test_split(X, y, test_size = 0.2)

  feature_1_train = get_feature_model2(np.array(X))

  model_classify = LogisticRegression(max_iter = 500)
  model_classify.fit(np.array(feature_1_train), y)


  Query_type = model_classify.predict(get_feature_model2(Query).reshape(1, -1))
  # .reshape(1, -1)
  # print(Query_type)[0]
  print(Query_type)
  return Query_type

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

def break_query(query, purpose_list):
  model = SentenceTransformer('bert-base-nli-mean-tokens')
  # !python -m spacy download en_core_web_trf
  nlp = spacy.load("en_core_web_trf")

  # query = "How much money can I spend for buying a car"
  query = unicodedata.normalize('NFKD', query)
  print("=================================")
  print("Before breaking")
  print("=================================")
  print(query)

  lower_query = query.lower()
  q_purpose = ""
  
  break_ind = -1
  tags = []
  tokens = []
  purpose_found = False

  # POS tagging
  doc = nlp(query)
  for token in doc:
      tokens.append(str(token))
      tags.append((str(token), token.pos_))

  f = -1
  # Extracting purpose and breaking
  for purpose in purpose_list:
    p = purpose.lower()
    doc_purp = nlp(purpose)
    token_purp = []
    for i in doc_purp:
      token_purp.append(str(i))
    ngram = len(token_purp)
    for i in range(len(tokens) - 1, ngram - 1, -1):
      str1 = " ".join(tokens[i - ngram + 1: i + 1])
      str2 = " ".join(token_purp)
      samples = [str1, str2]
      sentence_embeddings = model.encode(samples)
      sim = cosine_similarity([sentence_embeddings[0]], sentence_embeddings[1:])
      if float(sim[0][0]) > 0.9:
        f = i - ngram + 1
    if(f == -1):
      continue
    break

  # If purpose not found
  if f == -1:
    return "General Purpose", query  
  
  # Purpose found
  purpose_found = True
  print("Purpose = " + purpose)
  print()

  # Breaking the query
  doc = nlp(query)
  seg1 = ""


  # Rule based query division
  for i in range(len(doc) - 1, -1, -1):
    # print(i)
    if tags[i][1] == "ADP" or tags[i][0].lower() == "to":
        
      # Printing break word
      print("Break at \"" + str(tags[i][0]) + "\"")
      
      print("=================================")
      print("After breaking")
      print("=================================")
      # Printing the first segement
      print("First Segment:", end=" ")
      print(tokens[:i])
      # segement 1 to be sent to execute section for query generation
      seg1 = tokens[:i]

      # Printing the Second Segement
      print("Second segment:", end=" ")
      print(tokens[i:])
      #  segment 2 to be sent to the lookup data structure with the purpose p
      seg2 = tokens[i:]
      break
  
  return purpose, seg1

def run_evaluate(Query, purpose_list, userID):
  purpose, q2 = break_query(Query, purpose_list)
  q2s = q2.copy()
  q2s.extend(["from accountNo", str(userID)])
  q2s = " ".join(q2s)
  Query_type = classify_query(Query)
  return purpose, q2, q2s, Query_type

"""#Enforce"""

def withdraw_money(user, purpose, Lookup_table, users):
  # global Lookup_table
  perms = Lookup_table[purpose]
  user_perms = perms[0][user.pan_card]
  if not user_perms.withdraw_perm:
    print("Failed! you cannot withdraw money for this purpose")
    return -1
  todays_date = date.today()
  if todays_date.year < user_perms.time_withdraw:
    print("Failed! you cannot withdraw money for this purpose at the present time")
    return -1
  if user_perms.cap_withdraw != -1:
    print("Success! Withdrawing money for {0}".format(purpose))
    return user_perms.cap_withdraw
  print("Success! Withdrawing money for {0}".format(purpose))
  return perms[1]

def view_money(user, purpose, Lookup_table, users):
  # global Lookup_table
  perms = Lookup_table[purpose]
  user_perms = perms[0][user.pan_card]
  if not user_perms.view_perm:
    print("Failed! you cannot view money for this purpose")
    return -1
  print("Success! You can view money for this purpose.")
  return 1

def deposit_money(user, purpose, Lookup_table, users):
  # global Lookup_table
  perms = Lookup_table[purpose]
  user_perms = perms[0][user.pan_card]
  if not user_perms.deposit_perm:
    print("Failed! you cannot deposit money for this purpose")
    return -1
  todays_date = date.today()
  if todays_date.year < user_perms.time_deposit:
    print("Failed! you cannot deposit money for this purpose at the present time")
    return -1
  # if user_perms.cap_deposit != -1 and amount > user_perms.cap_deposit:
  #   print("Failed! You only have Rs {0} for this purpose.".format(user_perms.cap_deposit))
  #   return user_perms.cap_deposit

  if user_perms.cap_deposit != -1:
    print("Success! depositing money for {0}".format(purpose))
    return user_perms.cap_deposit
  print("Success! depositing money for {0}".format(purpose))
  return perms[1]


def run_enforce(Query, curr_user, userID, users, Lookup_table, purpose, Query_type):
    # global users
    # global Lookup_table
    # users = users
    # Lookup_table = Lookup_table
    # tokenizer = BertTokenizer.from_pretrained("QCRI/bert-base-multilingual-cased-pos-english")
    # model_pos = BertForTokenClassification.from_pretrained("QCRI/bert-base-multilingual-cased-pos-english")
    # class_pipe = pipeline(model = "QCRI/bert-base-multilingual-cased-pos-english", tokenizer = "QCRI/bert-base-multilingual-cased-pos-english", task = "token-classification")
    
    if Query_type == 0:
        output = withdraw_money(curr_user, purpose, Lookup_table, users)
    elif Query_type == 1:
        output = deposit_money(curr_user, purpose, Lookup_table, users)
    else:
        output = view_money(curr_user, purpose, Lookup_table, users)
    return output

"""#Execute"""

# Commented out IPython magic to ensure Python compatibility.
def view_execute(q2s, output):
  # Path to the NLP2sql models
  path_wikisql = "/content/drive/My Drive/NLP2SQLmodels"
  sqlite_db = create_engine('sqlite://',echo=False)

  uploaded_files = list(uploaded.keys())

  uploaded_file = None
  schema_types = []
  field_names = []

  if len(uploaded_files) > 0 :
    uploaded_file = uploaded_files[0]
    schema = getSchema(uploaded_file)
    schema_types = schema['schema_types']
    field_names = schema['field_names']

    # Add data to in memory sqllite database
    with open(uploaded_file, 'r') as file:
      data_df = pd.read_csv(file)
      data_df.to_sql('uploadedtable', con=sqlite_db, index=True, index_label='uploaded_id', if_exists='replace')
  else:
    print('No file has been uploaded')

  # Adapted from  https://colab.research.google.com/drive/1qYJTbbEXYFVdY6xae9Zmt96hkeW8ZFrn but with the training and testing removed

  !rm -rf RoBERTa-NL2SQL

  GIT_PATH = "https://github.com/aneesha/RoBERTa-NL2SQL"
  !git clone "{GIT_PATH}"
#   %cd RoBERTa-NL2SQL

  import load_data
  import torch
  import json,argparse
  import load_model
  import roberta_training
  import corenlp_local
  import seq2sql_model_testing
  import seq2sql_model_training_functions
  import model_save_and_infer
  import dev_function
  import infer_functions
  import time
  import os
  import nltk

  from dbengine_sqlnet import DBEngine
  from torchsummary import summary
  from tqdm.notebook import tqdm
  nltk.download('punkt')
  from nltk.tokenize import word_tokenize, sent_tokenize
  import warnings
  warnings.filterwarnings("ignore")

  device = torch.device("cuda")

  # load models
  roberta_model, tokenizer, configuration = load_model.get_roberta_model()          # Loads the RoBERTa Model
  seq2sql_model = load_model.get_seq2sql_model(configuration.hidden_size) 

  path_roberta_pretrained = path_wikisql + "/model_roberta_best.pt"
  path_model_pretrained = path_wikisql + "/model_best.pt"

  # load pre-trained weights
  if torch.cuda.is_available():
      res = torch.load(path_roberta_pretrained)
  else:
      res = torch.load(path_roberta_pretrained, map_location='cpu')

  roberta_model.load_state_dict(res['model_roberta'])

  if torch.cuda.is_available():
      res = torch.load(path_model_pretrained)
  else:
      res = torch.load(path_model_pretrained, map_location='cpu')

  seq2sql_model.load_state_dict(res['model'])
  table_id = 'uploadedtable'

  natural_language_query = q2s
  domainswap =['score']

  if 'score' in natural_language_query:
    natural_language_query = natural_language_query.replace('score', 'value')

  sqlqueries = infer_functions.infer(
                  natural_language_query,
                  table_id, field_names, schema_types, tokenizer, 
                  seq2sql_model, roberta_model, configuration, max_seq_length=222,
                  num_target_layers=2,
                  beam_size=4
              )

  sqlquery = sqlqueries[0]
  print('Generated SQL: ',sqlquery)

  aggs = ['count', 'avg', 'max', 'min', 'distinct']
  uniquelist = ['distinct','unique']


  if any([x in natural_language_query for x in uniquelist]):
    sqlquery = sqlquery.replace('SELECT ', 'SELECT distinct ')

  if not any(x in sqlquery for x in aggs):
    sqlquery = sqlquery.replace('SELECT ', 'SELECT *, ')

  print('Postprocessed SQL: ',sqlquery)

  df = pd.read_sql(sqlquery, sqlite_db)
  data_table.DataTable(df, include_index=False, num_rows_per_page=20)

def getSchema(filename):
  schema_types = []
  field_names = []
  schema = infer(filename, limit=500, headers=1, confidence=0.85)
  field_objs = schema['fields']
  for field in field_objs:
    field_names.append(field['name'])
    schema_type = field['type']
    if schema_type == 'string':
      schema_types.append('text')
    else:
      schema_types.append('real')
  return {'schema_types': schema_types,'field_names':field_names}


def withdraw_execute(Query, table, acc, amount):
  NER = spacy.load("en_core_web_trf")
  text1= NER(Query)
  amount_q = 0
  for word in text1.ents:
    if word.label_ == "MONEY" or word.label_ == "CARDINAL":
      amount_q = int(word.text)
      break
  if(amount == -1):
    print("Query cannot be executed")
    return
  if amount_q > amount:
    print("Max amount limit for withdrawl exceeded. Updating the amount.")
  amount = amount_q
  withdraw_stencil = "update " + str(table) + " set balance = balance - " + str(amount) + " where accountNo = " + str(acc)
  print("Final query: " + withdraw_stencil)
  return

def deposit_execute(Query, table, acc, amount):
  NER = spacy.load("en_core_web_trf")
  text1= NER(Query)
  amount_q = 0
  for word in text1.ents:
    if word.label_ == "MONEY" or word.label_ == "CARDINAL":
      amount_q = int(word.text)
      break
  if(amount == -1):
    print("Query cannot be executed")
    return
  if amount_q > amount:
    print("Max amount limit for withdrawl exceeded. Updating the amount.")
  amount = amount_q
  deposit_stencil = "update " + str(table) + " set balance = balance + " + str(amount) + " where accountNo = " + str(acc)
  print("Final query: " + deposit_stencil)
  return


def run_execute(q2, q2s, userID, output, Query_type):
    if Query_type == 0:
        withdraw_execute(" ".join(q2), "user_table", userID, output)
    elif Query_type == 1:
        deposit_execute(" ".join(q2), "user_table", userID, output)
    else:
        output = view_execute(q2s, output)

"""# Code to run"""

global users
global Lookup_table
users = []
Lookup_table = {}
def add_user(name, pan_no, relation, acc_no = -1):
  temp = User(name, pan_no, relation, acc_no)
  global users
  users.append(temp)
  return temp

# Creating the User class
class User:
  def __init__(self, name, pan_card, relation, acc_no = -1):
    
    # Initializing permissions
    self.name = name
    self.pan_card = pan_card
    self.relation = relation
    self.acc_no = acc_no

class UserPermissions:
  def __init__(self, u_pan, withdraw_perm = True, deposit_perm = True, view_perm = True, time_deposit = 0, time_withdraw = 0, cap_deposit = -1, cap_withdraw = -1):
    self.u_pan = u_pan
    self.withdraw_perm = withdraw_perm 
    self.deposit_perm = deposit_perm
    self.time_withdraw = time_withdraw 
    self.time_deposit = time_deposit 
    self.cap_withdraw = cap_withdraw 
    self.cap_deposit = cap_deposit
    self.view_perm = view_perm

# Setting up the data

root = add_user("Father", 1, "self")
wife = add_user("Wife", 2, "wife")
daughter = add_user("Daughter", 3, "daughter")
son = add_user("Son", 4, "son")

purpose1 = "Groceries"
purpose2 = "Self car"
purpose3 = "Wife's car"
purpose4 = "Son's college"
purpose5 = "Daughter's college"
purpose6 = "General Purpose"
purp_list = [purpose1, purpose2, purpose3, purpose4, purpose5, purpose6]

user_dict = {}


# Filling the lookup table
for i in users:
    if i.pan_card == 3 or i.pan_card == 4:
        user_dict[i.pan_card] = UserPermissions(i.pan_card, withdraw_perm = False, view_perm = False, deposit_perm = False)
    else:
        user_dict[i.pan_card] = UserPermissions(i.pan_card)
Lookup_table[purpose1] = (user_dict, 50000)


user_dict = {}

for i in users:
    if i.pan_card == 3 or i.pan_card == 4 or i.pan_card == 2:
        user_dict[i.pan_card] = UserPermissions(i.pan_card, withdraw_perm = False, view_perm = False, deposit_perm = False)
    else:
        user_dict[i.pan_card] = UserPermissions(i.pan_card)
Lookup_table[purpose2] = (user_dict, 100000)

user_dict = {}

for i in users:
    if i.pan_card == 3 or i.pan_card == 4 or i.pan_card == 1:
        user_dict[i.pan_card] = UserPermissions(i.pan_card, withdraw_perm = False, view_perm = False, deposit_perm = False)
    else:
        user_dict[i.pan_card] = UserPermissions(i.pan_card)
Lookup_table[purpose3] = (user_dict, 100000)

user_dict = {}
for i in users:
    if i.pan_card == 3:
        user_dict[i.pan_card] = UserPermissions(i.pan_card, deposit_perm = False)
    if i.pan_card == 1 or i.pan_card == 2:
        user_dict[i.pan_card] = UserPermissions(i.pan_card, withdraw_perm = False)
    else:
        user_dict[i.pan_card] = UserPermissions(i.pan_card)

Lookup_table[purpose4] = (user_dict, 8000)

user_dict = {}
for i in users:
    if i.pan_card == 4:
        user_dict[i.pan_card] = UserPermissions(i.pan_card, deposit_perm = False)
    if i.pan_card == 1 or i.pan_card == 2:
        user_dict[i.pan_card] = UserPermissions(i.pan_card, withdraw_perm = False)
    else:
        user_dict[i.pan_card] = UserPermissions(i.pan_card)

Lookup_table[purpose5] = (user_dict, 12000)

user_dict = {}
for i in users:
    user_dict[i.pan_card] = UserPermissions(i.pan_card)

Lookup_table[purpose6] = (user_dict, 100000)

Query = "Withdraw 100000 for my daughter's college fees"
print("Query to be used: " + Query)
userID = 1111111
purpose, q2, q2s, Query_type = run_evaluate(Query, purp_list, userID)

outputs = run_enforce(Query, daughter, userID, users, Lookup_table, purpose, Query_type)

run_execute(q2, q2s, userID, outputs, Query_type)