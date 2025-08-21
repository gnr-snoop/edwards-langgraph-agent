examples = [
    {
        "input": "Obtener la cantidad total de usuarios.", 
        "query": "SELECT COUNT(*) FROM users"
    },
    {
        "input": "¿Cuántas tareas fueron asignadas a Guillermo Rodriguez?",
        "query": "SELECT COUNT(*) FROM users JOIN assigned_to AS assignees ON id = user_id WHERE users.name = 'Guillermo Rodriguez'",
    },
    {
        "input": "Listar todas las tareas reportadas por Anabela Spegni.",
        "query": "SELECT tasks.* FROM tasks JOIN reported_by ON tasks.id = reported_by.task_id JOIN users ON users.id = reported_by.user_id WHERE users.name = 'Anabela Spegni'",
    },
    {
        "input": "Mostrar la cantidad de hallazgos clasificados por tipo.",
        "query": "SELECT COUNT(*) AS cantidad, tipo_hallazgo FROM tasks GROUP BY tipo_hallazgo",
    },
    {
        "input": "Mostrar las tareas que se encuentran en tratamiento junto con las personas asignadas.",
        "query": "SELECT tasks.id, tasks.name, users.name FROM tasks JOIN assigned_to ON tasks.id = assigned_to.task_id JOIN users ON assigned_to.user_id = users.id WHERE tasks.status = 'en tratamiento'",
    },
    {
        "input": "Mostrar las tareas que se encuentran abiertas junto con las personas asignadas.",
        "query": "SELECT tasks.id, tasks.name, users.name FROM tasks JOIN assigned_to ON tasks.id = assigned_to.task_id JOIN users ON assigned_to.user_id = users.id WHERE tasks.status = 'abierto'",
    },
    {
        "input": "Mostrar las tareas que se encuentran cerradas junto con las personas asignadas.",
        "query": "SELECT tasks.id, tasks.name, users.name FROM tasks JOIN assigned_to ON tasks.id = assigned_to.task_id JOIN users ON assigned_to.user_id = users.id WHERE tasks.status = 'cerrado'",
    },
    {
        "input": "¿Cuántas oportunidades de mejora hay con mas de 20 días?",
        "query": "SELECT COUNT(*) FROM tasks WHERE fecha_alta >= DATE_SUB(CURRENT_DATE(), INTERVAL 20 DAY)",
    },
    {
        "input": "¿Cuántos hallazgos tiene asignados Héctor Ferraro?",
        "query": "SELECT COUNT(*) FROM users JOIN assigned_to ON id = user_id WHERE name = 'Héctor Ferraro'",
    },
]
