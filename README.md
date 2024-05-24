# Alchemical Clone

Alchemical Clone is a Python tool designed to generate SQLAlchemy ORM code from existing databases. It automates the creation of Python ORM models by reflecting on your database's schema, making it ideal for kickstarting projects or documenting existing databases. It supports relationship inference, including many-to-many associations, and offers customizable naming conventions to align with your project's coding standards, as well as a simple plugin system.

## Features

- **Automatic ORM Code Generation**: Generate complete SQLAlchemy model code from your database schema.
- **Relationship Inference**: Automatically detects and generates relationships, including many-to-many associations.

## Installation

For now, instalation can only be done by cloning this git repository.

## Example Usage

The most basic way of running Alchemical Clone would be to import it and use it against a instance of an sqlalchemy.MetaData object:

```python
import alchemical_clone
import sqlalchemy

# Create a connection to the database
engine_url = alchemical_clone.utils.get_engine_url(
    dialect="mysql", 
    username="some_username", 
    password="some_password", 
    host="some_host", 
    port=3306
)
engine = sqlalchemy.create_engine(engine_url)

# Create a metadata object and reflect the database
metadata = sqlalchemy.MetaData()
metadata.reflect(bind=engine, schema="some_schema")

lab = alchemical_clone.AlchemicalLab(metadata)
lab.create_clone("clone")
```

Assuming this is the users table on your database, where the tables `languages` and `user_groups` also exist:

| Field       | Type             | Null | Key | Default | Extra          |
|-------------|------------------|------|-----|---------|----------------|
| id          | int(10) unsigned | NO   | PRI | NULL    | auto_increment |
| email       | varchar(45)      | NO   | UNI | NULL    |                |
| name        | varchar(45)      | YES  |     | NULL    |                |
| birthday    | datetime         | YES  |     | NULL    |                |
| userGroupId | int(10) unsigned | YES  | MUL | NULL    |                |
| langId      | int(10) unsigned | NO   | MUL | 1       |                |

The directory `clone` will be created, with the following files:
* `__init__.py` - A python file to mark this directory as a package
* `_base.py` - This file is used to define the SQL Alchemy declarative base
* `users.py`, `languages.py`, `user_groups.py` - one file for each table, with their definitions

The contents of the `users.py` file, for example, should be:

```python
from sqlalchemy import Column, DateTime, ForeignKeyConstraint, Index, Integer, PrimaryKeyConstraint, String
from sqlalchemy.orm import relationship

from ._base import Base


class Users(Base):
    __tablename__ = "users"
    __table_args__ = (
        PrimaryKeyConstraint("id"),
        ForeignKeyConstraint(["langId"], ["some_schema.languages.id"], name="fk_user_lang_id", onupdate="CASCADE"),
        ForeignKeyConstraint(["countryId"], ["some_schema.countries.id"], name="fk_user_country_id", onupdate="CASCADE"),
        ForeignKeyConstraint(["userGroupId"], ["some_schema.user_groups.id"], name="fk_user_group_id", onupdate="CASCADE"),
        {
            "schema": "some_schema",
        },
    )

    id = Column("id", Integer(), nullable=False)
    email = Column("email", String(length=45), nullable=False)
    name = Column("name", String(length=45), nullable=True)
    birthday = Column("birthday", DateTime(), nullable=True)
    userGroupId = Column("userGroupId", Integer(), nullable=True)
    langId = Column("langId", Integer(), nullable=False, server_default="'1'")

    fk_user_lang_id = relationship("Languages", foreign_keys=[langId])
    fk_user_country_id = relationship("Countries", foreign_keys=[countryId])
    fk_user_group_id = relationship("UserGroups", foreign_keys=[userGroupId])

Index("fk_user_lang_id_idx", Users.langId, unique=False)
Index("id_UNIQUE", Users.id, unique=True)
Index("email_UNIQUE", Users.email, unique=True)
Index("fk_user_group_id_idx", Users.userGroupId, unique=False)
```

## Plugins
There are currently two plugins available for Alchemical Clone - `one_to_many` and `many_to_many`. Both of them discover and add relationships of the stated type to the tables' class definitions. They can be used when calling `create_clone`:

```python
lab.create_clone("clone", plugins=[
    alchemical_clone.plugins.one_to_many,
    alchemical_clone.plugins.many_to_many,
])
```

### One to many
To illustrate the effect of the `one_to_many` plugin, let's consider the tables `users` and `orders`, where the `orders` table has a foreign key to `users`, so each user can have multiple orders. If the plugin is used, the lines marked with `!` will be added:

```python
...

class Orders(Base):
    __tablename__ = "orders"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="orders_pk"),
        ForeignKeyConstraint(["user_id"], ["users.id"], name="user_orders_fk"),
    )

    id = Column("id", Integer(), nullable=False)
    user_id = Column("user_id", Integer(), nullable=False)

    user_orders_fk = relationship("Users", foreign_keys=[user_id])

...

class Users(Base):
    __tablename__ = "users"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="users_pk"),
    )

    id = Column("id", Integer(), nullable=False)

    users_to_orders = relationship("Orders", back_populates="user_orders_fk", viewonly=True)  # !

...
```

With this, `Users.users_to_orders` will contain a list of orders where `user_id` matches the `Users` object's `id`.

### Many to many
The `many_to_many` plugin functions in a similar way. Let's say that, instead of orders, we have liked products. Now, it makes sense that a user might like multiple products and that a product may be liked by multiple users. We could represent this relationship using an intermediate table, "user_liked_product", resulting in the following:

```python
...

class Products(Base):
    __tablename__ = "products"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="products_pk"),
    )

    id = Column("id", Integer(), nullable=False)

    users_through_user_liked_product = relationship("User", secondary=UserLikedProduct.__table__, back_populates="products_through_user_liked_product", viewonly=True)  # !

...

class Users(Base):
    __tablename__ = "users"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="users_pk"),
    )

    id = Column("id", Integer(), nullable=False)

    products_through_user_liked_product = relationship("Products", secondary=UserLikedProduct.__table__, back_populates="users_through_user_liked_product", viewonly=True)  # !

...

class UserLikedProduct(Base):
    __tablename__ = "user_liked_product"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="users_pk"),
        ForeignKeyConstraint(["user_id"], ["users.id"], name="user_fk"),
        ForeignKeyConstraint(["product_id"], ["products.id"], name="product_fk"),
    )

    id = Column("id", Integer(), nullable=False)
    user_id = Column("user_id", Integer(), nullable=False)
    product_id = Column("product_id", Integer(), nullable=False)

    user_fk = relationship("Users", foreign_keys=[user_id])
    product_fk = relationship("Products", foreign_keys=[product_id])

...


```

With this, `Users.products_through_user_liked_product` will be a list of all the products the user liked, and `Products.users_through_user_liked_product` will be a list of all the users that liked a product.


## Progress

- [x] Simple ORM generation
- [ ] Database-specific optimizations
- [x] Plugin support
- [ ] Naming maps / configuration files
- [ ] Tests
