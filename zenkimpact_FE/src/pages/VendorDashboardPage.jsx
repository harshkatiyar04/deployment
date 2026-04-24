import React from 'react';
import Layout from '../components/Layout';
import VendorDashboardView from '../microservices/shared/VendorDashboardView';

export default function VendorDashboardPage() {
  return (
    <Layout>
      <VendorDashboardView />
    </Layout>
  );
}
