/**
 * Simple Test Component for Phase 5
 * Tests React/TypeScript configuration and basic component functionality
 */

import React from 'react';

interface TestComponentProps {
  title: string;
  message?: string;
}

const TestComponent: React.FC<TestComponentProps> = ({ title, message = 'Test successful!' }) => {
  return (
    <div className="test-component">
      <h2>{title}</h2>
      <p>{message}</p>
      <div className="test-info">
        <p>✅ React component compilation working</p>
        <p>✅ TypeScript types working</p>
        <p>✅ Props interface working</p>
      </div>
    </div>
  );
};

export default TestComponent;