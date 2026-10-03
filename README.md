Inventory & Warehouse Management System (IWMS)
DBMS Mini Project
Team ID: 23
Section: S6
Guide: Dr. Purushotham Muniganti

Team Members
Name Student ID

Varalakshmi K 2520030578 Himesh A 2520030317 Ishwak 2520030458

1. Project Overview
The Inventory & Warehouse Management System (IWMS) is a database-driven web application designed to manage products, suppliers, warehouses, stock movements and orders in a centralized relational database.

The system is intended to replace manual registers or scattered spreadsheets with structured database operations. It provides current stock visibility, transaction tracking, low-stock identification and reports.

The project applies core DBMS concepts including:

Relational database design
Primary keys and foreign keys
Normalization / 3NF-oriented design
CRUD operations
SQL queries and joins
Transactions
Referential integrity
Role-based access
Inventory movement tracking
2. Objectives
Maintain product, supplier, warehouse and order information without unnecessary duplication.
Record stock-in and stock-out transactions.
Keep inventory quantities updated after transactions.
Provide CRUD operations for important master data.
Generate stock, order and low-stock reports.
Provide Admin and Staff access with different permissions.
Maintain a history of stock movements for auditing.
3. Technology Stack
Frontend
HTML
CSS
JavaScript
Backend
PHP
Database
MySQL
Local Development Environment
Laragon (Apache + MySQL)
Recommended Browser
Google Chrome
Mozilla Firefox
Code Editor
Visual Studio Code
4. System Modules
4.1 User Management
Admin login
Staff login
Role-based access
Admin user management
Enable / disable user accounts
4.2 Product Management
Add product
Edit product
Search/view products
SKU management
Category assignment
Supplier assignment
Price management
Reorder-level management
Product archive
4.3 Supplier Management
Add supplier
Edit supplier
Delete supplier
Store supplier contact information
4.4 Customer Management
Add customer
Edit customer
Delete customer
Use customers in sales orders
4.5 Warehouse Management
Add warehouse
Edit warehouse
Delete warehouse
Store warehouse location
Store warehouse capacity
4.6 Stock Management
View stock by product and warehouse
Stock In
Stock Out
Validate available quantity
Prevent insufficient-stock sales
Record stock movement history
Update stock using database transactions
4.7 Order Management
Purchase Orders
Represents goods coming into the warehouse.

Effect: Stock quantity increases.

Sales Orders
Represents goods leaving the warehouse.

Effect: Stock quantity decreases.

The system rejects a sales transaction when the requested quantity is greater than the available stock.

4.8 Reports & Alerts
Current stock information
Low-stock alerts
Stock value
Purchase value
Sales value
Warehouse-wise stock
Top-selling products
Order history
5. Database Design
The system is based on a normalized relational structure.

Main Tables
users
categories
suppliers
customers
products
warehouses
stock
stock_movements
orders
order_items
Important Relationships
SUPPLIERS
    |
    | 1-to-many
    v
PRODUCTS
    |
    | 1-to-many
    v
STOCK
    ^
    |
    | many-to-1
WAREHOUSES


ORDERS
   |
   | 1-to-many
   v
ORDER_ITEMS
   |
   | many-to-1
   v
PRODUCTS
Primary keys uniquely identify records. Foreign keys connect related tables and maintain referential integrity.

6. Project Folder Structure
iwms_project/
│
├── api/
│   └── index.php
│
├── assets/
│   ├── style.css
│   └── app.js
│
├── database/
│   └── schema.sql
│
├── includes/
│   └── config.php
│
├── index.php
├── login.php
├── logout.php
├── setup.php
└── README.md
7. Installation & Execution Using Laragon
Step 1 --- Install Laragon
Install Laragon for Windows with Apache and MySQL support.

Step 2 --- Start Services
Open Laragon and click:

Start All
Make sure:

Apache = Running
MySQL  = Running
Step 3 --- Copy the Project
Copy the complete iwms_project folder to:

C:\laragon\www\
Final location:

C:\laragon\www\iwms_project\
Step 4 --- Initialize the Database
Open:

http://localhost/iwms_project/setup.php
Run the setup once.

Step 5 --- Open the Application
Open:

http://localhost/iwms_project/login.php
8. Demo Login Credentials
Admin
Username: admin
Password: admin123
Staff
Username: staff
Password: staff123
For a real deployment, replace demo credentials and protect or remove the setup page after initialization.

9. Recommended Project Review Demonstration
Use this sequence during the review:

Login
  ↓
Dashboard
  ↓
Products
  ↓
Suppliers
  ↓
Customers
  ↓
Warehouses
  ↓
Stock In
  ↓
Show Updated Stock
  ↓
Stock Out
  ↓
Show Updated Stock
  ↓
Purchase Order
  ↓
Sales Order
  ↓
Stock Movements
  ↓
Low-Stock Alerts
  ↓
Reports
  ↓
Staff Login / Role Restrictions
Best Live Demonstration
Select a product.
Note its current stock.
Perform Stock In.
Show the increased quantity.
Perform Stock Out.
Show the decreased quantity.
Open Stock Movements and show the transaction history.
Open Reports and show the updated database information.
Attempt a Stock Out greater than available stock to demonstrate validation.
10. Example SQL Query
Find Low-Stock Products
SELECT p.Name, s.Quantity
FROM PRODUCT p
JOIN STOCK s
ON p.ProductID = s.ProductID
WHERE s.Quantity < 10;
This query joins product information with stock information and identifies products below the selected stock threshold.

11. Data Integrity & Safety Features
The implementation uses:

Primary keys
Foreign keys
Unique constraints
Parameterized SQL
Database transactions
Quantity validation
Insufficient-stock protection
Stock movement/audit records
Role-based access
These mechanisms help maintain consistent inventory data and prevent invalid stock operations.

12. Expected System Behavior
Stock In
Previous Quantity + Incoming Quantity
= Updated Quantity
Stock Out
Previous Quantity - Outgoing Quantity
= Updated Quantity
Insufficient Stock
If:

Requested Quantity > Available Quantity
the transaction is rejected and stock is not incorrectly reduced.

Purchase Order
Purchase Order
      ↓
Stock In
      ↓
Stock Quantity Increases
Sales Order
Sales Order
      ↓
Stock Out
      ↓
Stock Quantity Decreases
13. Implementation Screenshots
Screenshot 1 --- Product / Stock Management Module
Recommended screen contents:

Product list
SKU
Category
Supplier
Price
Reorder level
Current stock
Stock In / Stock Out controls
Screenshot 2 --- Reports / Low-Stock Alert Module
Recommended screen contents:

Current stock
Low-stock products
Stock value
Purchase/sales totals
Warehouse-wise stock
Top-selling products
These screenshots should be taken from the actual running application.

14. Future Scope
The system can be extended with:

Barcode scanning
Mobile access
Predictive stock alerts
Historical sales-based inventory prediction
15. Project Review --- Short Explanation
Our project is an Inventory and Warehouse Management System developed using a relational database approach. It manages products, suppliers, warehouses, stock movements and orders. The system supports stock-in and stock-out operations, purchase and sales orders, low-stock alerts and reports. Primary keys and foreign keys are used to maintain relationships between tables, while normalization reduces unnecessary duplication. The main purpose is to provide centralized and updated inventory information instead of relying on manual records.

16. Common Viva Questions
What is the main purpose of the project?
To manage warehouse inventory, stock movements, suppliers and orders using a centralized relational database.

Why did you use a relational database?
Because the system contains related entities such as products, suppliers, warehouses, stock and orders that can be represented efficiently using tables and relationships.

What is a primary key?
A field that uniquely identifies a record in a table.

What is a foreign key?
A field that references a key in another table and establishes a relationship between the tables.

Why normalization?
To reduce unnecessary duplication and improve data consistency.

What happens during Stock In?
The available quantity of the selected product in the selected warehouse increases.

What happens during Stock Out?
The available quantity decreases after validating that sufficient stock exists.

What happens if there is insufficient stock?
The transaction is rejected so the inventory quantity is not reduced below the available amount.

How are low-stock products identified?
The current stock quantity is compared with the configured reorder/low-stock threshold.

What is the role of SQL in the project?
SQL is used to insert, update, retrieve and relate data and to generate reports from the database.

17. Conclusion
The Inventory & Warehouse Management System demonstrates how DBMS concepts can be applied to a practical warehouse problem. It provides structured data storage, controlled inventory transactions, relational integrity, reporting and low-stock visibility through a web-based interface.

Project: Inventory & Warehouse Management System (IWMS)
Team ID: 23
Section: S6
Guide: Dr. Purushotham Muniganti
