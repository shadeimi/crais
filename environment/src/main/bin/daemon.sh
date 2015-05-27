#!/bin/bash

# The following two lines are used by the chkconfig command. Change as is
# appropriate for your application.  They should remain commented.
# chkconfig: 345 20 80

CRAISNSPIDFILE="${crais.root}/crais_ns.pid"
CRAISPIDFILE="${crais.root}/crais.pid"
                                                                                                                                                                                 
start() {

		# Delete all *.pyc first
		find ${static.service.home} -name "*.pyc" -exec rm -rf {} \;
		
        chmod +x ${appium.bin}
        chmod +x ${crais.root}/bin/*
        chmod +x ${static.service.home}/conf/crais.py
        touch ${crais.root}/lib64/python2.7/site-packages/zope/__init__.py 
        chown jmailer:jmailer ${crais.root}/lib64/python2.7/site-packages/zope/__init__.py
        
       
    if [ -f ${CRAISNSPIDFILE} ] && [[ "kill -s 0 `cat -- ${CRAISNSPIDFILE}` &>/dev/null" ]];
    then
    	echo "CRAIS NS System is still up.."
        exit 1
    else
    	echo "Starting CRAIS NS Service.."
    	su - jmailer -c \
    	"export PYTHONPATH=${crais.root}/lib/python2.7/site-packages/crais/code:${crais.root}/lib/python2.7/site-packages:${crais.root}/lib64/python2.7/site-packages:${PYTHONPATH} \
    	&& PYTHONPATH=${crais.root}/lib/python2.7/site-packages:${crais.root}/lib/python2.7/site-packages/crais/code:${crais.root}/lib64/python2.7/site-packages:${PYTHONPATH} \
    	PATH=${crais.root}/bin/:${PATH} \
        scl enable python27 '${static.service.home}/bin/pyro4-ns -n ${crais.address} -p ${crais.nsport} &'"
    fi

	echo "Wait for CRAIS NS Startup.."
	sleep 5  

    if [ -f ${CRAISPIDFILE} ] && [[ "kill -s 0 `cat -- ${CRAISPIDFILE}` &>/dev/null" ]];
    then
    	echo "CRAIS Server is still up.."
        exit 1
    else
    	echo "Starting CRAIS Server.."
    	su - jmailer -c \
    	"export PYTHONPATH=${crais.root}/lib/python2.7/site-packages/engine:${crais.root}/lib/python2.7/site-packages:${crais.root}/lib64/python2.7/site-packages:${PYTHONPATH} \
    	&& PYTHONPATH=${crais.root}/lib/python2.7/site-packages:${crais.root}/lib64/python2.7/site-packages:${PYTHONPATH} \
    	PATH=${crais.root}/bin/:${PATH} \
        scl enable python27 'python ${static.service.home}/conf/crais.py rpc &'"
    fi

}                                                                                                                                                                                   
                                                                                                                                                                                    
stop() {                                                                                                                                                                            
        if [ -f ${CRAISNSPIDFILE} ]; then
    		echo "Stopping CRAIS NS System.."
    		kill `cat -- ${CRAISNSPIDFILE}`
    		sleep 2
	    	rm -f -- ${CRAISNSPIDFILE}  
	    fi  
	    
	    if [ -f ${CRAISPIDFILE} ]; then
    		echo "Stopping CRAIS Server.."
    		kill `cat -- ${CRAISPIDFILE}`
    		sleep 2
	    	rm -f -- ${CRAISPIDFILE}  
	    fi

	    #Kill all jmailer local processes, just to be sure
		killall -u jmailer
		killall adb
	                                                                                                                                          
}    

init() {   
        echo 'CRAIS Server initialization'
        useradd crais -s /bin/false -m -d /jhub/_prod/server_ptiqa_crais_daemon -u 700 && echo onh2l5gj5jk5p75t2tah2j3s | passwd crais --stdin

        # TODO: Add unit-test launching using tox / nose

}

status() {
        if [ -f ${CRAISNSPIDFILE} ] && [[ "kill -s 0 `cat -- ${CRAISNSPIDFILE}` &>/dev/null" ]];
        then
            echo "CRAIS NS System is running"
        else
            echo "CRAIS NS System is DOWN"
            exit 1
        fi
        
        if [ -f ${CRAISPIDFILE} ] && [[ "kill -s 0 `cat -- ${CRAISPIDFILE}` &>/dev/null" ]];
        then
            echo "CRAIS Server is running"
        else
            echo "CRAIS Server is DOWN"
            exit 1
        fi
}                                                                                                                                 

query() {
    	su - jmailer -c \
    	"export PYTHONPATH=${crais.root}/lib/python2.7/site-packages/engine:${crais.root}/lib/python2.7/site-packages:${crais.root}/lib64/python2.7/site-packages:${PYTHONPATH} \
    	&& PYTHONPATH=${crais.root}/lib/python2.7/site-packages:${crais.root}/lib64/python2.7/site-packages:${PYTHONPATH} \
    	PATH=${crais.root}/bin/:${PATH} \
        scl enable python27 'python ${static.service.home}/conf/crais.py query'"
}         
                                                                                                                                                                                                                                                                                                                                                                 
case "$1" in                                                                                                                                                                        
    start)                                                                                                                                                                          
        $1
        ;;                                                                                                                                                                          
    stop)                                                           
        $1                                                                                                                                                                          
        ;;  
    restart)
        stop
        sleep 2
		start
        ;;
    init)
    	$1
    	;;
    query)
    	$1
    	;;
    status)
    	$1
    	;;                                                                                                                                                                     
    *)                                                                                                                                                                              
        echo $"Usage: $0 {start|stop|restart|shell|init}"                                                                                                                                      
        exit 2                                                                                                                                                                      
esac 
