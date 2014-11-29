#ifndef __SIEGE_H_20141128200244__
#define __SIEGE_H_20141128200244__

#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <iostream>
#include <memory>
#include <sstream>
#include <algorithm>
#include <string>
#include <vector>
#include <set>
#include <map>

class Siege {
public:
    Siege() {}
    virtual ~Siege() {}
    
    int run(const std::string& host, short port, int threadCount, int concurrent, int reps, int msgCmd);

private:
    void* threadWorkerProxy(void* args);

    // 真正的worker
    void threadWorker();

private:
    std::string& m_host;
    short m_port;
    int m_threadCount;
    int m_concurrent;
    int m_reps;
    int m_msgCmd;
};

#endif
