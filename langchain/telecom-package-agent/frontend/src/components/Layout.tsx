import React from "react";
import { Layout as AntLayout, Menu } from "antd";
import { Link, useLocation } from "react-router-dom";

const { Header, Content } = AntLayout;

const items = [
  { key: "/chat", label: <Link to="/chat">对话</Link> },
  { key: "/dashboard", label: <Link to="/dashboard">仪表盘</Link> },
  { key: "/packages", label: <Link to="/packages">套餐列表</Link> },
  { key: "/benefits", label: <Link to="/benefits">权益中心</Link> }
];

interface Props {
  children: React.ReactNode;
}

const Layout: React.FC<Props> = ({ children }) => {
  const location = useLocation();

  return (
    <AntLayout className="min-h-screen">
      <Header className="flex items-center">
        <div className="text-white font-semibold mr-8">
          Telecom Package Agent
        </div>
        <Menu
          theme="dark"
          mode="horizontal"
          selectedKeys={[location.pathname]}
          items={items}
        />
      </Header>
      <Content className="p-6">{children}</Content>
    </AntLayout>
  );
};

export default Layout;

