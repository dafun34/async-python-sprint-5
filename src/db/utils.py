def sa_row_to_dict(row):
    """Преобразовать табличное представление sa записи в словарь."""
    dictionary = {}
    for column in row.__table__.columns:
        dictionary[column.name] = str(getattr(row, column.name))

    return dictionary
