#include "Flood.h"

Flood::Flood() {
    m_port = 0;
    m_threadCount = 0;
    m_concurrent = 0;
    m_reps = 0;
    m_msgCmd = 0;
}

Flood::~Flood() {

}

int Flood::run(const std::string& host, short port, int threadCount, int concurrent, int reps, int msgCmd) {
    m_host = host;
    m_port = port;
    m_threadCount = threadCount;
    m_concurrent = concurrent;
    m_reps = reps;
    m_msgCmd = msgCmd;

    // TODO 启动线程
}
