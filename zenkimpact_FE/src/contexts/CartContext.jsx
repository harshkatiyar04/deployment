import React, { createContext, useContext, useState } from 'react';

const CartContext = createContext();

export const useCart = () => {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error('useCart must be used within a CartProvider');
  }
  return context;
};

export const CartProvider = ({ children }) => {
  const [studentCart, setStudentCart] = useState([]);
  const [personalCart, setPersonalCart] = useState([]);

  // Mock member metadata to simulate who added it
  const currentMember = {
    id: 'u-101',
    name: 'Ananya D.',
    role: 'Member'
  };

  const addToStudentCart = (product, comment) => {
    setStudentCart(prev => [
      ...prev,
      {
        cartId: `sc_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        product,
        addedBy: currentMember,
        comment: comment,
        addedAt: new Date().toISOString()
      }
    ]);
  };

  const addToPersonalCart = (product) => {
    setPersonalCart(prev => [
      ...prev,
      {
        cartId: `pc_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        product,
        addedBy: currentMember,
        addedAt: new Date().toISOString()
      }
    ]);
  };

  const removeFromCart = (cartId, type) => {
    if (type === 'student') {
      setStudentCart(prev => prev.filter(item => item.cartId !== cartId));
    } else {
      setPersonalCart(prev => prev.filter(item => item.cartId !== cartId));
    }
  };

  const clearCart = (type) => {
    if (type === 'student') setStudentCart([]);
    if (type === 'personal') setPersonalCart([]);
    if (type === 'all') {
      setStudentCart([]);
      setPersonalCart([]);
    }
  };

  const cartTotalCount = studentCart.length + personalCart.length;

  const value = {
    studentCart,
    personalCart,
    addToStudentCart,
    addToPersonalCart,
    removeFromCart,
    clearCart,
    cartTotalCount
  };

  return (
    <CartContext.Provider value={value}>
      {children}
    </CartContext.Provider>
  );
};
