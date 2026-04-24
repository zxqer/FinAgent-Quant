#include <iostream>
#include <memory>
#include <string>
#include <thread>
#include <chrono>

#include <grpcpp/grpcpp.h>
#include "fin_agent.grpc.pb.h"

using grpc::Server;
using grpc::ServerBuilder;
using grpc::ServerContext;
using grpc::ServerWriter;
using grpc::Status;
using finagent::FinAgentService;
using finagent::DataEnvelope;
using finagent::MarketData;
using finagent::Empty;

// --- 核心服务实现类 ---
class FinAgentServiceImpl final : public FinAgentService::Service {
    
    // 实现服务端流式接口：StreamFinancialData
    Status StreamFinancialData(ServerContext* context, 
                               const Empty* request, 
                               ServerWriter<DataEnvelope>* writer) override {
        
        std::cout << "[Server] Client connected, starting data stream..." << std::endl;

        // 模拟高频行情数据推送
        double btc_price = 65000.0;
        int counter = 0;

        while (!context->IsCancelled()) { // 检查客户端是否还在连接
            DataEnvelope envelope;
            MarketData* market = envelope.mutable_market();
            
            // 1. 模拟数据更新
            btc_price += (rand() % 100 - 50) * 0.1; // 随机波动
            market->set_symbol("BTC/USDT");
            market->set_price(btc_price);
            market->set_volume(1.5 + (rand() % 10));
            
            // 设置时间戳 (面试加分点：对时间的精确处理)
            auto now = std::chrono::system_clock::now();
            auto seconds = std::chrono::duration_cast<std::chrono::seconds>(now.time_since_epoch());
            market->mutable_timestamp()->set_seconds(seconds.count());

            // 2. 发送数据
            if (!writer->Write(envelope)) {
                // 如果写入失败（如客户端断开），退出循环
                break;
            }

            std::cout << "[Stream] Sent Tick #" << ++counter << ": " << btc_price << std::endl;

            // 3. 控制频率 (模拟 10Hz 推送)
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            
            // 演示每 50 次推送插入一条模拟“新闻”
            if (counter % 50 == 0) {
                DataEnvelope news_envelope;
                auto news = news_envelope.mutable_news();
                news->set_source("MarketWatch");
                news->set_title("Bitcoin volatility increasing!");
                news->set_content("Heavy trading activity detected in the last minute.");
                writer->Write(news_envelope);
            }
        }

        std::cout << "[Server] Stream ended." << std::endl;
        return Status::OK;
    }
};

// --- 启动函数 ---
void RunServer() {
    std::string server_address("0.0.0.0:50051"); // 监听所有网卡
    FinAgentServiceImpl service;

    ServerBuilder builder;
    // 监听端口，不使用 SSL（本地测试用 Insecure）
    builder.AddListeningPort(server_address, grpc::InsecureServerCredentials());
    // 注册服务
    builder.RegisterService(&service);

    // 面试加分项：性能调优
    // builder.SetMaxSendMessageSize(10 * 1024 * 1024); // 设置最大发送消息大小

    std::unique_ptr<Server> server(builder.BuildAndStart());
    std::cout << "Server listening on " << server_address << std::endl;

    // 等待服务器关闭
    server->Wait();
}

int main(int argc, char** argv) {
    // 设置随机种子
    srand(static_cast<unsigned int>(time(NULL)));
    
    RunServer();
    return 0;
}