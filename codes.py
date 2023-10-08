import os
import zipfile
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import xml.dom.minidom as minidom
import xml.etree.ElementTree as ET
import base64
import sqlite3

def read_document(file_path):
    with open(file_path, 'rb') as file:
        return file.read()

def encrypt_document(data, key):
    cipher = AES.new(key, AES.MODE_EAX)
    nonce = cipher.nonce
    ciphertext, tag = cipher.encrypt_and_digest(data)
    return nonce, ciphertext, tag

def convert_to_xml(nonce, ciphertext, tag):
    root = ET.Element("encrypted_document")
    ET.SubElement(root, "nonce").text = base64.b64encode(nonce).decode('utf-8')
    ET.SubElement(root, "ciphertext").text = base64.b64encode(ciphertext).decode('utf-8')
    ET.SubElement(root, "tag").text = base64.b64encode(tag).decode('utf-8')

    xml_string = ET.tostring(root, encoding='utf-8')
    return xml_string

def parse_xml(xml_string):
    dom_tree = minidom.parseString(xml_string)
    root = dom_tree.documentElement

    nonce = base64.b64decode(root.getElementsByTagName("nonce")[0].childNodes[0].data)
    ciphertext = base64.b64decode(root.getElementsByTagName("ciphertext")[0].childNodes[0].data)
    tag = base64.b64decode(root.getElementsByTagName("tag")[0].childNodes[0].data)

    return nonce, ciphertext, tag

def compress_data(xml_string, output_file):
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr("data.xml", xml_string)

def create_table():
    #Connect to the SQLite database (or create it if it doesn't exist)
    conn = sqlite3.connect("file_index.db")
    cursor = conn.cursor()

    # Create a table to store the file information
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS files ("
            "id INTEGER PRIMARY KEY,"
            "file_name TEXT,"
            "xml_data TEXT )"
    )

    #Commit changes and close the connection
    conn.commit()
    conn.close()

def insert_file_data(file_name, xml_data):
    # Connect to the SQLite database
    conn = sqlite3.connect("file_index.db")
    cursor = conn.cursor()

    # Insert the file data into the 'files' table
    cursor.execute("INSERT INTO files (file_name, xml_data) VALUES (?, ?)", (file_name, xml_data))

    # Commit changes and close the connection
    conn.commit()
    conn.close()

def index_file(file_path, xml_file_path):
    # Read the XML data from the compressed XML file
    with open(xml_file_path, 'rb') as xml_file:
        xml_data = xml_file.read()

    # Get the file name from the file path
    file_name = os.path.basename(file_path)

    # Insert the file data and XML representation into the database
    insert_file_data(file_name, xml_data)

def main():
    # Step 1: Take the document as input
    document_file = "C:\\Users\\adhar\\OneDrive\\Desktop\\Life+goals+worksheet.pdf"
    document_data = read_document(document_file)

    # Step 2: Encrypt the document using AES
    encryption_key = get_random_bytes(16)  # 128-bit key
    nonce, ciphertext, tag = encrypt_document(document_data, encryption_key)

    # Step 3: Convert file data to XML using XSLT
    xml_string = convert_to_xml(nonce, ciphertext, tag)

    # Step 4: Parse the XML using DOM
    parsed_nonce, parsed_ciphertext, parsed_tag = parse_xml(xml_string)

    # Step 5: Compress the XML data using Zip
    xml_file = "encrypted_document.xml"
    compress_data(xml_string, xml_file)

    # Step 6: Indexing the file
    index_file(document_file, xml_file)
import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, send_file

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DATABASE'] = 'dms_database.db'


def create_tables():
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()

    # Create the 'documents' table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            filename TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()


def get_documents():
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()

    cursor.execute('SELECT id, title, content, filename FROM documents')
    documents = cursor.fetchall()

    conn.close()

    return documents


def add_document(title, content, filename):
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()

    cursor.execute('INSERT INTO documents (title, content, filename) VALUES (?, ?, ?)', (title, content, filename))

    conn.commit()
    conn.close()


def delete_document(doc_id):
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()

    cursor.execute('SELECT filename FROM documents WHERE id = ?', (doc_id,))
    filename = cursor.fetchone()

    if filename:
        cursor.execute('DELETE FROM documents WHERE id = ?', (doc_id,))
        conn.commit()
        conn.close()
        return filename[0]

    conn.close()
    return None


def update_document(doc_id, title, content, filename):
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()

    cursor.execute('UPDATE documents SET title=?, content=?, filename=? WHERE id=?', (title, content, filename, doc_id))

    conn.commit()
    conn.close()


@app.route('/')
def index():
    documents = get_documents()
    return render_template('index.html', documents=documents)


@app.route('/document/<int:doc_id>')
def document_detail(doc_id):
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()

    cursor.execute('SELECT id, title, content, filename FROM documents WHERE id = ?', (doc_id,))
    document = cursor.fetchone()

    conn.close()

    if document:
        return render_template('document_detail.html', document=document)
    else:
        return "Document not found.", 404


@app.route('/add_document', methods=['GET', 'POST'])
def add_document():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        file = request.files['document_file']
        filename = file.filename

        # Save the uploaded file to the 'uploads' folder
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        add_document(title, content, filename)
        return redirect(url_for('index'))

    return render_template('add_document.html')


@app.route('/document/<int:doc_id>/delete', methods=['POST'])
def delete_document_route(doc_id):
    filename = delete_document(doc_id)
    if filename:
        # Delete the uploaded file from the 'uploads' folder
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.remove(file_path)

    return redirect(url_for('index'))


@app.route('/document/<int:doc_id>/edit', methods=['GET', 'POST'])
def edit_document(doc_id):
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()

    cursor.execute('SELECT id, title, content, filename FROM documents WHERE id = ?', (doc_id,))
    document = cursor.fetchone()

    conn.close()

    if not document:
        return "Document not found.", 404

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        file = request.files['document_file']
        filename = file.filename

        if filename:
            # Save the uploaded file to the 'uploads' folder
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
        else:
            filename = document[3]  # Use the existing filename if no new file is uploaded

        update_document(doc_id, title, content, filename)
        return redirect(url_for('document_detail', doc_id=doc_id))

    return render_template('edit_document.html', document=document)


@app.route('/download/<int:doc_id>')
def download_document(doc_id):
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()

    cursor.execute('SELECT filename FROM documents WHERE id = ?', (doc_id,))
    filename = cursor.fetchone()

    conn.close()

    if filename:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename[0])
        return send_file(file_path, as_attachment=True, attachment_filename=filename[0])

    return "Document not found.", 404


if __name__ == '_main_':
    # Create the 'uploads' folder if it doesn't exist
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    create_tables()
    app.run(debug=True)


if __name__ == "__main__":
    create_table()
    main()
