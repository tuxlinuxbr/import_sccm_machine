import_sccm_machine
===================

Este script conecta na base SQL Server do Microsoft System Center Configuration Manager e importa as máquinas, 
atrelando aos usuários já importados no sistema do GLPI.

Utilização:
Edite o script e altere as variáreis de conexão ao banco SQL Server onde está configurado o SCCM:
* mssql_db
* mssql_user
* mssql_pass
Altere também as variáreis de conexão ao banco MySQL onde está configurado o GLPI:
* mysql_db
* mysql_user
* mysql_pass

Agende a sincronização na crontab do servidor linux para ser executado de tempos em tempos (12 em 12 horas).
