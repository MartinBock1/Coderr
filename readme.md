# Coderr API

Welcome to the Coderr API, a robust backend service built with Django and Django Rest Framework. This API powers a platform designed to connect business service providers with customers, managing everything from user profiles and service offers to orders and reviews.

![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)
![Django REST Framework](https://img.shields.io/badge/Django%20REST%20Framework-A30000?style=for-the-badge&logo=django&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)

---

## 📖 Table of Contents

-   [About The Project](#about-the-project)
-   [Key Features](#key-features)
-   [Technical Overview](#technical-overview)
-   [API Endpoints](#api-endpoints)
-   [Getting Started](#getting-started)
    -   [Prerequisites](#prerequisites)
    -   [Installation](#installation)
-   [Running the Server](#running-the-server)
-   [Running Tests](#running-tests)
-   [API Documentation](#api-documentation)

---

## 🚀 About The Project

The Coderr API provides the complete backend infrastructure for a service-based marketplace. It handles user authentication, profile management for both 'customer' and 'business' roles, creation and management of service offers, order processing, and a review system. The architecture is modular, with each core feature encapsulated in its own Django app, ensuring scalability and maintainability.

---

## ✨ Key Features

-   **Token-Based Authentication**: Secure user registration and login using DRF's AuthToken.
-   **Role-Based Access Control (RBAC)**: Distinct permissions for 'customer' and 'business' user types. Businesses can create offers, while customers can place orders and write reviews.
-   **Full CRUD Functionality**: Comprehensive Create, Read, Update, and Delete operations for all key resources like profiles, offers, orders, and reviews.
-   **Nested Data Handling**: Advanced serializers for creating and updating related objects in a single request (e.g., creating an Offer with its three pricing tiers).
-   **Advanced Filtering and Searching**: Endpoints for lists (like `/api/offers/`) support dynamic filtering by fields like price, creator, delivery time, and full-text search on titles and descriptions.
-   **Automated Profile Creation**: A signal-based system ensures that every new user automatically gets a corresponding profile, guaranteeing data consistency.
-   **Aggregated Platform Statistics**: A dedicated endpoint (`/api/base-info/`) provides a public-facing dashboard with key platform metrics.
-   **Comprehensive Test Suite**: A robust set of unit and integration tests to ensure API reliability and correctness.

---

## 🛠️ Technical Overview

The project is structured into several Django apps, each responsible for a specific domain:

-   `user_auth_app`: Manages user registration and login.
-   `profile_app`: Handles user profiles, differentiating between 'customer' and 'business' roles. This is the single source of truth for profile data.
-   `offers_app`: Manages the creation and display of services offered by business users.
-   `orders_app`: Manages the process of customers ordering services from businesses.
-   `reviews_app`: Allows customers to leave reviews for businesses.
-   `platform_stats_app`: Provides aggregated data for the entire platform.

A **post-save signal** on the `User` model automatically creates a `Profile` instance for every new user, ensuring data integrity across the application. Custom permission classes (`IsBusinessUser`, `IsCustomerUser`, `IsOwnerOrReadOnly`) enforce the business logic and secure the endpoints.

---

## 🌐 API Endpoints

A summary of the main API endpoints available:

| Method | Endpoint                                   | Description                                          |
| :----- | :----------------------------------------- | :--------------------------------------------------- |
| `POST` | `/api/registration/`                       | Register a new user.                                 |
| `POST` | `/api/login/`                              | Log in and receive an authentication token.          |
| `GET`  | `/api/profiles/business/`                  | Get a list of all business profiles.                 |
| `GET`  | `/api/profiles/customer/`                  | Get a list of all customer profiles.                 |
| `GET/PATCH` | `/api/profile/{user_id}/`             | Retrieve or update a specific user's profile.        |
| `GET/POST` | `/api/offers/`                         | List all offers or create a new one.                 |
| `GET/PATCH/DELETE` | `/api/offers/{id}/`            | Retrieve, update, or delete a specific offer.        |
| `GET/POST` | `/api/orders/`                         | List a user's orders or create a new one.            |
| `PATCH/DELETE` | `/api/orders/{id}/`                | Update or delete a specific order.                   |
| `GET/POST` | `/api/reviews/`                        | List all reviews or create a new one.                |
| `PATCH/DELETE` | `/api/reviews/{id}/`               | Update or delete a specific review.                  |
| `GET`  | `/api/base-info/`                          | Get aggregated platform-wide statistics.             |

---


## 🏁 Getting Started

Follow these instructions to get a local copy of the project up and running for development and testing.

### Prerequisites

Before you get started, make sure you have the following installed:

- Python 3.8 or later
- Django 3.2 or later
- PostgreSQL or another compatible database

### Installation

1. **Clone the repository:**

   ```bash
   git clone <REPOSITORY-LINK>
   cd <projectfolder>
   
2. **Set up a virtual environment:**

    ```bash
    python -m venv env
    env/Scripts/activate  # Windows
    source env/bin/activate  # macOS/Linux
Note: On macOS/Linux, python3 may have to be used instead of python.

3.  **Install the required packages:**
    The `requirements.txt` file contains all necessary Python packages.
    ```bash
    pip install -r requirements.txt
    ```
    *Note: If a `requirements.txt` file is not present, you can generate one from the existing project setup using `pip freeze > requirements.txt`.*

4. **Apply database migrations:**
    This will create the necessary database tables (using SQLite by default).
    ```bash
    python manage.py migrate
    ```

## 🖥️ Running the Server

To start the local development server, run the following command from the project's root directory:

```bash
python manage.py runserver
```
Tip: If errors occur, check the `settings.py` for paths, database settings or forgotten `.env` files.

Now, you can access the application at http://localhost:8000.

## 📚 API Documentation
This project uses drf-spectacular to automatically generate OpenAPI 3.0 documentation. Once the server is running, you can access the interactive API documentation at:

```bash
Swagger UI: http://127.0.0.1:8000/api/docs/
ReDoc: http://127.0.0.1:8000/api/redoc/
```
These interfaces allow you to explore all available endpoints, view their expected request/response formats, and even execute API calls directly from your browser.

### License
This project is licensed under the MIT License – see the LICENSE file for details.
