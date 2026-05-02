import React from 'react';
import Layout from '../components/Layout';
import { usePersona } from '../contexts/PersonaContext';
import EducationalMarketplace from '../microservices/shared/EducationalMarketplace';

export default function Marketplace() {
  const { isSponsor } = usePersona();
  return (
    <Layout>
      <EducationalMarketplace isLeader={isSponsor} />
    </Layout>
  );
}
