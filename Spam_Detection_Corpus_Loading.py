# imports to determine functionality
import pandas as pd
import numpy as np
from os import path
from re import sub
from email import message_from_file, policy
from email.parser import BytesParser
from glob import glob
import nltk
from sklearn.feature_extraction.text import TfidfVectorizer


# spamassassin email corpus -
# based on code from https://medium.com/@thiagolcmelo/train-you-own-spam-detector-57725e8e81c0 -
# train your own spam detector

ham_dir = path.join('data', 'ham')
spam_dir = path.join('data', 'spam')

print('hams:', len(glob(f'{ham_dir}/*')))  # hams: 6952
print('spams:', len(glob(f'{spam_dir}/*')))  # spams: 2399

# define classes for functionality
class StandardEmail:
    def __init__(self, subject: str, body: str, origin: str, destination: str):
        self.destination = destination
        self.origin = origin
        self.subject = subject
        self.body = body

    @property
    def clean(self):
        sanitizer = '[^A-Za-z]+'
        clean = sub(sanitizer, ' ', f'{self.subject} {self.body} {self.origin} {self.destination}')
        clean = clean.lower()
        return sub('\s+', ' ', clean)

    @property
    def structured_clean(self):
        sanitizer = '[^A-Za-z]+'
        subject = sub(sanitizer, ' ', f'{self.subject}').lower().lstrip()
        body = sub(sanitizer, ' ', f'{self.body}').lower().lstrip()
        origin = sub(sanitizer, ' ', f'{self.origin}').lower().lstrip()
        destination = sub(sanitizer, ' ', f'{self.destination}').lower().lstrip()

        return [sub('\s+', ' ', origin), sub('\s+', ' ', destination), sub('\s+', ' ', subject), sub('\s+', ' ', body)]

    def __str__(self):
        subject = f'subject: {self.subject}'
        body_first_line = self.body.split('\n')[0]
        body = f'body: {body_first_line}...'
        return f'{subject}\n{body}'

    def __repr__(self):
        return self.__str__()

# cycle through and read each email into memory
class EmailIterator:
    def __init__(self, directory: str):
        self._files = glob(f'{directory}/*')
        self._pos = 0

    def __iter__(self):
        self._pos = -1
        return self

    def __next__(self):
        if self._pos < len(self._files) - 1:
            self._pos += 1
            return self.parse_email(self._files[self._pos])
        raise StopIteration()

    @staticmethod
    def parse_email(filename: str) -> StandardEmail:
        with open(filename,
                  encoding='utf-8',
                  errors='replace') as fp:
            message = message_from_file(fp)

        subject = None
        for item in message.keys():
            if item == 'Subject':
                subject = item

        if message.is_multipart():
            body = []
            for b in message.get_payload():
                body.append(str(b))
            body = '\n'.join(body)
        else:
            body = message.get_payload()

        return StandardEmail(subject, body, message["From"], message["To"])

# load emails into memory

ham_emails = EmailIterator('data/ham')

spam_emails = EmailIterator('data/spam')

# now we have two lists of emails
# forgo loading hams for testing -----------------------
# print("Loading Ham Emails into Memory Please Wait...")
# hams = [email.structured_clean for email in ham_emails]

# loading spams for testing ----------------------------
print("Loading Spam Emails into memory Please Wait...")
spams = [email.structured_clean for email in spam_emails]

# ▚▚▚▚ Exploratory Data Analysis ▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚

# HAM
# XXX #

# SPAM
Spam_Subject = []
Spam_Body = []
Spam_From = []
Spam_To = []
for item in spams:
    Spam_From.append(item[0])
    Spam_To.append(item[1])
    Spam_Subject.append(item[2])
    Spam_Body.append(item[3])

Spam_Dictionary = {"From": Spam_From, "To": Spam_To, "Subject": Spam_Subject, "Body": Spam_Body}
Spam_DataFrame = pd.DataFrame(Spam_Dictionary)

# Preprocessing and Feature Engineering ########################################################

# A3M Update: Function to load and parse emails
# BytesParser is pythons email parser where policy=default suits all typical email parsing tasks.
def load_emails(directory):
    emails = []
    for filename in glob(f'{directory}/*'):
        with open(filename, 'rb') as file:
            msg = BytesParser(policy=policy.default).parse(file)
        # Email parts parsing
        subject = msg.get('subject', '')
        email_from = msg.get('from', '')
        email_to = msg.get('to', '')
        # Body:
        if msg.is_multipart():
            content = ''.join(part.get_payload(decode=True).decode('utf-8', errors='ignore')
                              for part in msg.get_payload() if part.get_content_type() == 'text/plain')
        else:
            content = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        # Combining all parts
        full_content = f'Subject: {subject} From: {email_from} To: {email_to} {content}'
        emails.append(full_content)
    return emails

# A3M Add: Loading and preprocessing data
ham_emails = load_emails(ham_dir)
spam_emails = load_emails(spam_dir)

# A3M Add: Combining ham and spam emails into a dataFrame
labels = ['ham'] * len(ham_emails) + ['spam'] * len(spam_emails)
all_emails = ham_emails + spam_emails
data = pd.DataFrame({
    'email': all_emails,
    'label': labels
})

# A3M Add: Preprocessing and cleaning (removing non alphabet chars) the email content
data['clean_email'] = data['email'].apply(lambda x: sub('[^A-Za-z]+', ' ', x).lower().strip())

# A3M Add: Handling missing values 2Feb2024;2:17pm
print('Mising Values before:')
print(data.isnull().sum())
data['clean_email'].fillna('', inplace=True)
print('Mising Values after:')
print(data.isnull().sum())

# A3M Add: Handling duplicates 2Feb2024;2:17pm
print('Duplicates before:')
print(data.duplicated().sum())
data.drop_duplicates(inplace=True)
print('Duplicates after:')
print(data.duplicated().sum())

# Feature Extraction ###################################################################################

# A3M Update: Feature extraction using TF IDF and stopwords handling
nltk.download('stopwords')
from nltk.corpus import stopwords
stop_words = stopwords.words('english')
vectorizer = TfidfVectorizer(stop_words=stop_words, max_features=100)  # Could be more than 100
features = vectorizer.fit_transform(data['clean_email'])

# A3M Add: Converting the features to a DataFrame
features_df = pd.DataFrame(features.toarray(), columns=vectorizer.get_feature_names_out())

# A3M Add: Combining features with the original data (email content and label)
final_data = pd.concat([data.reset_index(drop=True), features_df], axis=1)

# A3M Add: Printing final dataset with feature scores
print("Features obtained with TF IDF")
print(final_data)

#############################################################################################################
# A3M Add: Other testing and insights of a more refined feature engineering

# Calculating the average TF IDF score for each feature (word)
# Idea would be to find words with the highest TF IDF score as these should be the most significant in diff spam vs ham
# Next we could filter this out and train base solely on this top n features to further avoid overfitting
# We could also convert label feature to binary ham=1 and spam=0 to help on the training
# For now we could train as is and see how good it performs

mean_tfidf = final_data.drop(columns=['email', 'label', 'clean_email']).mean().sort_values(ascending=False)
# A3M Add: Selecting top n features
top_n_features = 20  # We can change this
top_features = mean_tfidf.head(top_n_features)

print("Top features obtained with TF IDF")
print(top_features)