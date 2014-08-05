import pymssql
import mysql.connector
import base64
import sys

### Variaveis ###
# Entidade Default
defaultEntitie=4
# Conexao ao SQL Server
mssql_db='SERVER'
mssql_user='userconnect'
mssql_pass='userpassword'
# Conexao ao Mysql
mysql_db='SERVER'
mysql_user='userconnect'
mysql_pass='userpassword'
# Hardware info
selectHardwareInformation = "SELECT v_GS_SYSTEM_CONSOLE_USER.ResourceID AS [COMPUTERID], \
    v_R_System_Valid.Netbios_Name0 AS [COMPUTERNAME], \
    SUBSTRING(v_GS_SYSTEM_CONSOLE_USER.SystemConsoleUser0,CHARINDEX('\\',v_GS_SYSTEM_CONSOLE_USER.SystemConsoleUser0)+1,LEN(v_GS_SYSTEM_CONSOLE_USER.SystemConsoleUser0)) AS [USERNAME], \
    v_GS_SYSTEM_ENCLOSURE_UNIQUE.SerialNumber0 AS [SERIALNUMBER], \
    v_GS_COMPUTER_SYSTEM.TimeStamp AS [DATAMOD],\
    v_GS_COMPUTER_SYSTEM.Model0 AS [MODEL], \
    v_RA_System_IPSubnets.IP_Subnets0 AS [SUBNET] \
    FROM v_GS_SYSTEM_CONSOLE_USER \
        INNER JOIN v_FullCollectionMembership ON v_FullCollectionMembership.ResourceID = v_GS_SYSTEM_CONSOLE_USER.ResourceID \
        INNER JOIN v_R_System_Valid ON v_R_System_Valid.ResourceID = v_GS_SYSTEM_CONSOLE_USER.ResourceID \
        LEFT JOIN v_GS_SYSTEM_CONSOLE_USAGE_MAXGROUP ON v_GS_SYSTEM_CONSOLE_USAGE_MAXGROUP.ResourceID = v_GS_SYSTEM_CONSOLE_USER.ResourceID \
        LEFT JOIN v_GS_SYSTEM_ENCLOSURE_UNIQUE ON v_GS_SYSTEM_ENCLOSURE_UNIQUE.ResourceID = v_R_System_Valid.ResourceID \
        LEFT JOIN v_GS_COMPUTER_SYSTEM ON v_GS_COMPUTER_SYSTEM.ResourceID = v_R_System_Valid.ResourceID \
        LEFT JOIN v_RA_System_SMSAssignedSites ON v_RA_System_SMSAssignedSites.ResourceID = v_R_System_Valid.ResourceID \
        LEFT JOIN v_Site ON v_Site.SiteCode=v_RA_System_SMSAssignedSites.SMS_Assigned_Sites0 \
        LEFT JOIN v_RA_System_IPSubnets ON v_RA_System_IPSubnets.ResourceID=v_GS_SYSTEM_CONSOLE_USER.ResourceID \
    WHERE v_FullCollectionMembership.CollectionID = 'SMS00001' \
        AND v_GS_SYSTEM_CONSOLE_USAGE_MAXGROUP.TotalConsoleTime0 != 0 \
        AND (cast(v_GS_SYSTEM_CONSOLE_USER.TotalUserConsoleMinutes0 AS Decimal (20,4)))/(cast(v_GS_SYSTEM_CONSOLE_USAGE_MAXGROUP.TotalConsoleTime0 AS Decimal(20,4))) >= .51 \
        AND v_RA_System_IPSubnets.IP_Subnets0 IN ('172.16.0.0','192.168.2.0','192.168.100.0','192.168.101.0','192.168.102.0','192.168.103.0','192.168.104.0','192.168.105.0','192.168.105.0','192.168.107.0','192.168.108.0','192.168.109.0','192.168.110.0','192.168.10.0') \
    ORDER BY v_R_System_Valid.Netbios_Name0"

# Network Interface SQL
selectNetworkInformation = "Select v_GS_NETWORK_ADAPTER.Description0 AS [DESC], \
    v_GS_NETWORK_ADAPTER.MACAddress0 AS [MAC] \
    FROM v_GS_NETWORK_ADAPTER \
        LEFT Join v_GS_COMPUTER_SYSTEM on v_GS_COMPUTER_SYSTEM.ResourceID = v_GS_NETWORK_ADAPTER.ResourceID \
    WHERE \
        v_GS_NETWORK_ADAPTER.MACAddress0 IS NOT NULL \
        AND (v_GS_NETWORK_ADAPTER.AdapterType0 = 'Ethernet 802.3') \
        AND v_GS_NETWORK_ADAPTER.ServiceName0 NOT IN ('NdisWan','RasSstp','RasPppoe','tunnel','NdisrdMP','vwifimp','PSched','tmcfw','VBoxNetFlt','VBoxNetAdp') \
        AND v_GS_NETWORK_ADAPTER.ResourceID=%s"

### Funcoes ####
#
# Retorna o ID da Entidade que a maquina percente, conforce subnet
#
def returnEntitiesID(subnet):
    try:
        cursorMysql.execute("""SELECT ID FROM glpi_entities WHERE comment LIKE '%%%s%%'""" % (subnet,))
        entitie = cursorMysql.fetchall()
    except:
        return defaultEntitie
    if (len(entitie)<1):
        return defaultEntitie
    else:
        return entitie[0][0]

#
# Retorna o ID do modelo do equipamento
# caso nao exista este modelo na base, insere
#
def returnComputerModels(computerModel):
    try:
        cursorMysql.execute("""SELECT ID FROM glpi_computermodels WHERE name = '%s'""" % (computerModel,))
        model = cursorMysql.fetchall()
    except:
        return 0
    if (len(model)<1):
        cursorMysql.execute("""INSERT INTO glpi_computermodels(name) VALUES('%s')""" % (computerModel))
        mysql_conn.commit()
        return returnComputerModels(model)
    else:
        return model[0][0]
#
# Retorna o ID cadastrado no banco do usuario 'dono' da maquina
#
def returnUserID(userName):
    try:
        cursorMysql.execute("""SELECT ID FROM glpi_users WHERE name = '%s'""" % (userName,))
        userId = cursorMysql.fetchall()
    except:
        return 'NULL'
    if (len(userId)<1):
        return 'NULL'
    else:
        return userId[0][0]
# 
# Retorna o ID da maquina no banco
# se ja existir uma cadastrada com o mesmo nome/serial
#
def searchHardware(computer):
    try:
        cursorMysql.execute("""SELECT ID FROM glpi_computers WHERE name = '%s' AND serial = '%s'""" % (computer['COMPUTERNAME'],computer['SERIALNUMBER']))
        ret = cursorMysql.fetchall()
        if(len(ret)<1):
            return 0
        else:
            return ret[0][0]
    except:
        return 0

#
# Insere as configuracoes de rede da maquina
# necessario para criar os graficos no FusionSNMP
#
def insertNetworkCard(netInfo,computer):
        try:
            sqlNet = "INSERT INTO `glpi`.`glpi_networkports`(`items_id`,`itemtype`,`entities_id`,`name`,`mac`) \
        VALUES ('%s','Computer','%s','%s','%s')" % (computer['COMPUTERGLPIID'],computer['ENTITIEID'],netInfo[0],netInfo[1].lower())
            cursorMysql.execute(sqlNet)
            mysql_conn.commit()
        except Exception as e:
            print "%s" %(e)
        
#
# Insere as configuracoes de rede da maquina
# necessario para criar os graficos no FusionSNMP
#
def networkCard(computer,action='insert'):
    cursorNetwork.execute(selectNetworkInformation % (computer['COMPUTERID']))
    netInfo = cursorNetwork.fetchone()
    while netInfo:
        if(action.find('update')>-1):
            cursorMysql.execute("""SELECT ID FROM `glpi`.`glpi_networkports` WHERE `name`='%s' AND `items_id` = '%s'""" % (netInfo[0],computer['COMPUTERGLPIID']))
            ret = cursorMysql.fetchall()
            if(len(ret)<1):
                print '\tAdicionando interface de rede %s com mac %s.' % (netInfo[0], netInfo[1])
                insertNetworkCard(netInfo,computer)
        else:
            insertNetworkCard(netInfo,computer)
        netInfo = cursorNetwork.fetchone()

#
# Insere a maquina efetivamente no banco
#
def insertHardware(computer):
    sqlHwInsert = "INSERT INTO `glpi`.`glpi_computers`(`entities_id`,`name`,`serial`,`otherserial`,\
                `contact`,`contact_num`,`users_id_tech`,`groups_id_tech`,`comment`,`date_mod`,\
                `operatingsystems_id`,`operatingsystemversions_id`,`operatingsystemservicepacks_id`,\
                `os_license_number`,`os_licenseid`,`autoupdatesystems_id`,`locations_id`,`domains_id`,\
                `networks_id`,`computermodels_id`,`computertypes_id`,`is_template`,`template_name`,`manufacturers_id`,\
                `is_deleted`,`notepad`,`is_ocs_import`,`users_id`,`groups_id`,`states_id`,`ticket_tco`,`uuid`)\
                VALUES('%s','%s','%s',NULL,NULL,NULL,0,0,NULL,NOW(),0,0,0,NULL,NULL,0,0,1,0,'%s',1,0,NULL,0,0,NULL,0,'%s',0,0,0,NULL)" % (computer['ENTITIEID'],computer['COMPUTERNAME'],computer['SERIALNUMBER'],returnComputerModels(computer['MODEL']),computer['USERID'])
    cursorMysql.execute(sqlHwInsert)
    mysql_conn.commit()
    computer['COMPUTERGLPIID']=searchHardware(computer)    
    networkCard(computer)
    
#
# Altera o id do usuario na base
# neste caso, tambem altera as interfaces de rede, adicionando novas interfaces
#
def updateComponent(component,computer):
    if (component.find('glpi_computers')>-1):
        sql="UPDATE `%s` SET `users_id`='%s' WHERE `ID`='%s'" % (component,computer['USERID'],computer['COMPUTERGLPIID'])
        try:
            cursorMysql.execute(sql)
            mysql_conn.commit()
            print '\tAtualizando usuario %s na estacao %s.' % (computer['USERNAME'], computer['COMPUTERNAME'])
        except Exception, e:
            print 'Erro ao atualizar a estacao %s: %s' % (computer['COMPUTERNAME'],e)
    elif (component.find('glpi_networkports')>-1):
        networkCard(computer,'update')

#
# Verifica se mudou o usuario dono da estacao e altera no computador
#
def updateHardware(computer):
    try:
        cursorMysql.execute("""SELECT ID FROM `glpi`.`glpi_computers` WHERE `users_id`='%s' AND `name`='%s'""" % (computer['USERID'],computer['COMPUTERNAME']))
        ret = cursorMysql.fetchall()
    except Exception, e:
        print 'Erro durante o select: %s' % (e)
        ret = []
    if (len(ret)<1):
        print "Atualizando estacao ", computer['COMPUTERNAME']
        updateComponent('glpi_computers',computer)
        updateComponent('glpi_networkports',computer)
    else:
        print "Ignorando estacao ", computer['COMPUTERNAME']
       
#
### Corpo pricipal ###
# 
# Cria as conexoes, 1 para cada SQL pois serao executados em paralelo
try:
    mssql_conn0 = pymssql.connect(host=mssql_db, user=mssql_user, password=mssql_pass, as_dict=True)
    mssql_conn1 = pymssql.connect(host=mssql_db, user=mssql_user, password=mssql_pass)
    mysql_conn = mysql.connector.connect(host=mysql_db,user=mysql_user,password=mysql_pass,database='glpi')
    # Cursores
    cursorHardware = mssql_conn0.cursor()
    cursorNetwork = mssql_conn1.cursor()
    cursorMysql = mysql_conn.cursor()
    # Select na base do SQLServer
    cursorHardware.execute(selectHardwareInformation)
    hwInfo = cursorHardware.fetchone_asdict()
except:
    mssql_conn0.close()
    mssql_conn1.close()
    mysql_conn.close()
    sys.exit(1)

while hwInfo:
    computer = hwInfo
    computer['COMPUTERGLPIID'] = searchHardware(hwInfo)
    computer['USERID'] = returnUserID(computer['USERNAME'])
    computer['ENTITIEID']=returnEntitiesID(computer['SUBNET'])
    if(computer['COMPUTERGLPIID']<1):
        print "Adicionando estacao ", computer['COMPUTERNAME']
        insertHardware(computer)
    else:
        updateHardware(computer)
    del(computer)
    hwInfo = cursorHardware.fetchone_asdict()
    
# Fechando conexoes com os bancos
mssql_conn0.close()
mssql_conn1.close()
mysql_conn.close()
