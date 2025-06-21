// Função para finalizar pedido
async function submitOrder(orderData) {
    try {
        const response = await fetch('/api/place_order', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(orderData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Mostrar modal de confirmação
            document.getElementById('confirmationModal').classList.remove('hidden');
            
            // Limpar carrinho
            cart = [];
            updateCartCount();
            updateCartDisplay();
        } else {
            Swal.fire({
                icon: 'error',
                title: 'Erro no pedido',
                text: 'Houve um problema ao processar seu pedido. Por favor, tente novamente.'
            });
        }
    } catch (error) {
        console.error('Error:', error);
        Swal.fire({
            icon: 'error',
            title: 'Erro de conexão',
            text: 'Não foi possível conectar ao servidor. Verifique sua conexão com a internet.'
        });
    }
}

// Modifique a função de submit do formulário de checkout para usar a API
document.getElementById('checkoutForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    // Obter dados do formulário
    const nome = document.getElementById('nomeCliente').value;
    const rua = document.getElementById('ruaCliente').value;
    const numero = document.getElementById('numeroCasa').value;
    const bairro = document.getElementById('bairroCliente').value;
    const complemento = document.getElementById('complementoCliente').value;
    const telefone = document.getElementById('telefoneCliente').value;
    const paymentMethod = document.querySelector('input[name="payment"]:checked').value;
    const trocoPara = document.getElementById('trocoPara')?.value || '';
    
    // Preparar itens do carrinho
    const items = cart.map(item => ({
        id: item.id,
        name: item.name,
        price: item.price,
        quantity: item.quantity
    }));
    
    // Calcular total
    const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    const total = subtotal + deliveryFee;
    
    // Criar objeto de pedido
    const orderData = {
        customer_name: nome,
        customer_address: `${rua}, ${numero}, ${bairro}` + (complemento ? ` (${complemento})` : ''),
        customer_phone: telefone,
        items: items,
        total: total,
        payment_method: paymentMethod,
        change_for: paymentMethod === 'dinheiro' ? trocoPara : null
    };
    
    // Enviar pedido
    submitOrder(orderData);
});