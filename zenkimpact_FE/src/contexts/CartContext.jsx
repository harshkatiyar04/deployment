import React, { createContext, useContext, useState, useEffect } from 'react';
import apiClient from '../utils/apiClient';

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
  const [isLoading, setIsLoading] = useState(false);

  const fetchCart = async () => {
    const token = sessionStorage.getItem('zenk_token') || localStorage.getItem('zenk_token');
    if (!token) return;

    try {
      setIsLoading(true);
      const data = await apiClient.get('/vendor/cart');
      const mapCartItem = (item) => ({
        cartId: item.id,
        product: {
          ...item.product,
          image: item.product.image_url,
          studentPrice: item.product.student_price,
          memberPrice: item.product.discounted_price || item.product.price
        },
        comment: item.comment,
        addedAt: item.created_at
      });

      const studentItems = data.filter(item => item.cart_type === 'student').map(mapCartItem);
      const personalItems = data.filter(item => item.cart_type === 'personal').map(mapCartItem);
      setStudentCart(studentItems);
      setPersonalCart(personalItems);
    } catch (err) {
      console.error("Fetch Cart Error:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCart();
  }, []);

  const addToStudentCart = async (product, comment) => {
    try {
      await apiClient.post('/vendor/cart', {
        product_id: product.id,
        quantity: 1,
        cart_type: 'student',
        comment: comment
      });
      fetchCart();
    } catch (err) {
      console.error("Add to Student Cart Error:", err);
    }
  };

  const addToPersonalCart = async (product) => {
    try {
      await apiClient.post('/vendor/cart', {
        product_id: product.id,
        quantity: 1,
        cart_type: 'personal'
      });
      fetchCart();
    } catch (err) {
      console.error("Add to Personal Cart Error:", err);
    }
  };

  const removeFromCart = async (cartId, type) => {
    try {
      await apiClient.delete(`/vendor/cart/${cartId}`);
      fetchCart();
    } catch (err) {
      console.error("Remove from Cart Error:", err);
    }
  };

  const clearCart = async (type) => {
    try {
      const query = type !== 'all' ? `?cart_type=${type}` : '';
      await apiClient.delete(`/vendor/cart${query}`);
      fetchCart();
    } catch (err) {
      console.error("Clear Cart Error:", err);
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
    cartTotalCount,
    isLoading
  };

  return (
    <CartContext.Provider value={value}>
      {children}
    </CartContext.Provider>
  );
};
