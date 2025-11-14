/**
 * Home Page Component
 * Simple welcome page for testing
 */

import React from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { useNavigate } from 'react-router-dom';

const HomePage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="home-page p-p-4">
      <Card 
        title="歡迎使用 PDLS"
        subTitle="專案開發日誌記錄系統"
        className="p-text-center"
      >
        <p className="p-mb-4">
          這是一個專為開發團隊設計的專案管理和日誌記錄系統。
        </p>
        
        <div className="p-d-flex p-gap-3 p-jc-center">
          <Button
            label="建立新專案"
            icon="pi pi-plus"
            onClick={() => navigate('/projects/create')}
          />
          
          <Button
            label="查看範例專案"
            icon="pi pi-eye"
            className="p-button-outlined"
            onClick={() => navigate('/projects/1')}
          />
        </div>
      </Card>
    </div>
  );
};

export default HomePage;