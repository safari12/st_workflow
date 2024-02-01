## Introduction

The workflow library offers a framework for defining and executing asynchronous workflows. It simplifies chaining multiple tasks, handling errors, and managing shared context across tasks. This library is especially useful for designing complex workflows with multiple steps and dependencies.

## Features

- **Asynchronous Execution**: Define and execute tasks asynchronously.
- **Scopes**: Steps for normal execution, error handling, and exit scenarios.
- **Execution Modes**: Different modes like threads or processes.
- **Context Sharing**: Shared context (`ctx`) across all steps.
- **Retry Mechanism**: Retry steps upon failure.
- **Timeouts**: Set timeout limits.
- **Parallel Execution**: Concurrent execution of steps.
- **Cancellation**: Cancel workflows midway.

## Installation

```
pip install st-workflow
```

## Quick Start

Use `asyncio.run` to execute the workflow:

```python
import asyncio
from workflow import Workflow, Scope

# Define your steps
async def step1(ctx):
    # Your code here
    pass

async def error_step(ctx):
    # Your code here
    pass

# Create a workflow with a context
wf = Workflow(ctx={'initial_data': 'data_value'})

# Add steps to the workflow
wf.add_step(step1)
wf.add_error_step(error_step)

# Run the workflow using asyncio.run
asyncio.run(wf.run())
```

## Detailed Usage

### Enums

- `Scope`: Determines the scope of a step. Available values:

  - `NORMAL`: Steps that are executed as part of the main flow.
  - `ERROR`: Steps that are executed when an error occurs in the main flow.
  - `EXIT`: Steps that are always executed at the end, irrespective of success or error in the main flow.

- `ExecutionMode`: Determines how the step is executed.
  - `THREAD`: Executes the step in a thread.
  - `PROCESS`: Executes the step in a separate process.

### Workflow Class

The main class you'll be interacting with. It provides methods to define, manage, and execute steps.

#### Methods

- `add_step(func, scope, name, timeout, retries, cont_on_err)`: Add a step to the workflow.
- `add_error_step(func, name, timeout, retries)`: Shortcut to add a step with the ERROR scope.
- `add_exit_step(func, name, timeout, retries)`: Shortcut to add a step with the EXIT scope.
- `run()`: Start the execution of the workflow. Use it with `asyncio.run` for synchronous execution.
- `cancel()`: Cancel the ongoing workflow.

## Complex Example Without Workflow Library

```python
import asyncio

async def validate_order(order_id):
    # Order validation logic
    print(f"Validating order {order_id}")
    return True

async def process_payment(order_id, retries=3):
    # Payment processing with retries
    for attempt in range(retries):
        try:
            print(f"Processing payment for order {order_id}, attempt {attempt + 1}")
            return "Payment successful"
        except Exception as e:
            if attempt + 1 == retries:
                raise

async def check_stock(item_id):
    # Stock checking logic
    print(f"Checking stock for item {item_id}")
    return True

async def send_notification(user_id, message):
    # Notification sending logic
    print(f"Sending notification to user {user_id}: {message}")

async def main_workflow(order_id, item_id, user_id):
    try:
        if not await validate_order(order_id):
            raise Exception("Order validation failed")

        payment_status = await process_payment(order_id)
        stock_available, _ = await asyncio.gather(check_stock(item_id), send_notification(user_id, "Order received"))

        if not stock_available:
            raise Exception("Item out of stock")

        await send_notification(user_id, f"Order processed: {payment_status}")
    except asyncio.CancelledError:
        print("Workflow cancelled")
    except Exception as e:
        await send_notification(user_id, f"Order processing failed: {e}")

# Run the workflow
workflow_task = asyncio.create_task(main_workflow("order123", "item456", "user789"))
# Cancelling the workflow for demonstration (in a real scenario, the cancellation condition would be different)
asyncio.run(asyncio.sleep(1))
workflow_task.cancel()
asyncio.run(workflow_task)
```

## Complex Example With Workflow Library

```python
import asyncio
from your_library_name import Workflow, Scope

async def validate_order(ctx):
    order_id = ctx["order_id"]
    print(f"Validating order {order_id}")
    ctx["order_valid"] = True

async def process_payment(ctx):
    order_id = ctx["order_id"]
    print(f"Processing payment for order {order_id}")
    ctx["payment_status"] = "Payment successful"

async def check_stock(ctx):
    item_id = ctx["item_id"]
    print(f"Checking stock for item {item_id}")
    ctx["stock_available"] = True

async def send_order_received_notification(ctx):
    user_id = ctx["user_id"]
    message = "Order received"
    print(f"Sending notification to user {user_id}: {message}")

async def send_order_processed_notification(ctx):
    user_id = ctx["user_id"]
    message = f"Order processed: {ctx['payment_status']}"
    print(f"Sending notification to user {user_id}: {message}")

async def handle_error(ctx):
    user_id = ctx["user_id"]
    error_message = f"Order processing failed: {ctx.get('error_message', 'Unknown Error')}"
    print(f"Sending notification to user {user_id}: {error_message}")

wf = Workflow(ctx={"order_id": "order123", "item_id": "item456", "user_id": "user789"})

wf.add_step(validate_order)
wf.add_step(process_payment, retries=3)  # Retries for payment processing
wf.add_parallel_steps([check_stock, send_order_received_notification], name="stock_and_notification")  # Parallel execution
wf.add_step(send_order_processed_notification)
wf.add_error_step(handle_error)

# Run the workflow
workflow_task = asyncio.create_task(wf.run())
# Cancelling the workflow for demonstration
asyncio.run(asyncio.sleep(1))
wf.cancel()  # Workflow cancellation
asyncio.run(workflow_task)
```

## Real-World Examples

### 1. Web Scraping Workflow

Imagine you want to scrape data from a website, process it, store it in a database, and then notify someone about the update.

```python
import asyncio
from workflow import Workflow, Scope

async def fetch_data(ctx):
    # Use an HTTP library to fetch data from a website
    data = "fetched data"
    return data

async def process_data(ctx):
    # Process the fetched data
    processed_data = ctx["fetch_data"] + " processed"
    return processed_data

async def store_in_db(ctx):
    # Store the processed data in a database
    print(f"Stored: {ctx['process_data']}")

async def notify_someone(ctx):
    # Notify someone about the update
    print("Notification sent!")

# Error handler
async def handle_error(ctx):
    print(f"Error in step {ctx['normal_error']['step']}: {ctx['normal_error']['error']}")

wf = Workflow(ctx={})

wf.add_step(fetch_data)
wf.add_step(process_data)
wf.add_step(store_in_db)
wf.add_step(notify_someone)
wf.add_error_step(handle_error)

asyncio.run(wf.run())
```

### 2. Data Processing Pipeline

Imagine you're working with a large dataset. You need to load it, clean it, transform it, and then generate a report.

```python
import asyncio
from workflow import Workflow, Scope

async def load_data(ctx):
    # Load data from a source
    data = "raw data"
    return data

async def clean_data(ctx):
    # Clean the loaded data
    cleaned_data = ctx["load_data"].replace("raw", "cleaned")
    return cleaned_data

async def transform_data(ctx):
    # Transform the cleaned data
    transformed_data = ctx["clean_data"] + " transformed"
    return transformed_data

async def generate_report(ctx):
    # Generate a report based on the transformed data
    print(f"Report for {ctx['transform_data']} generated!")

# Error handler
async def handle_error(ctx):
    print(f"Error in step {ctx['normal_error']['step']}: {ctx['normal_error']['error']}")

wf = Workflow(ctx={})

wf.add_step(load_data)
wf.add_step(clean_data)
wf.add_step(transform_data)
wf.add_step(generate_report)
wf.add_error_step(handle_error)

asyncio.run(wf.run())
```

### 3. Infrastructure Management Workflow

Imagine you're managing a cloud infrastructure. You need to create a virtual machine, configure it, deploy an application, and monitor its status.

```python
import asyncio
from workflow import Workflow, Scope

async def create_vm(ctx):
    # Create a virtual machine
    vm_id = "vm123"
    return vm_id

async def configure_vm(ctx):
    # Configure the virtual machine
    print(f"Configured VM with ID: {ctx['create_vm']}")

async def deploy_app(ctx):
    # Deploy an application on the VM
    print(f"Deployed app on VM with ID: {ctx['create_vm']}")

async def monitor_status(ctx):
    # Monitor the status of the deployed app
    print("Monitoring app status...")

# Error handler
async def handle_error(ctx):
    print(f"Error in step {ctx['normal_error']['step']}: {ctx['normal_error']['error']}")

wf = Workflow(ctx={})

wf.add_step(create_vm)
wf.add_step(configure_vm)
wf.add_step(deploy_app)
wf.add_step(monitor_status)
wf.add_error_step(handle_error)

asyncio.run(wf.run())
```

## Advanced Real-World Example: E-commerce Order Processing System

---

Imagine an e-commerce system where a user places an order. The system needs to:

1. Validate the order.
2. Charge the user's credit card.
3. Notify the warehouse for packaging.
4. Notify the shipping company for delivery.
5. Notify the user about the order status.
6. If any step fails, it should handle the error appropriately.

For our example, we'll also incorporate features like retries, timeouts, parallel execution, and shared context.

```python
import asyncio
from workflow import Workflow, Scope

# Steps

async def validate_order(ctx):
    # Validate the order details
    print("Order validated!")
    return "Validated order details"

async def charge_credit_card(ctx):
    # Simulate credit card charge
    print("Credit card charged!")
    return "Transaction ID: 123456"

async def notify_warehouse(ctx):
    # Notify warehouse for packaging
    print("Warehouse notified for packaging!")

async def notify_shipping(ctx):
    # Notify shipping company for delivery
    print("Shipping company notified for delivery!")

# Parallel step
async def notify_user(ctx):
    # Notify user about order status in parallel
    print("User notified about order status!")

async def send_email(ctx):
    # Send an email confirmation to the user in parallel
    print("Email confirmation sent to user!")

# Error handler
async def handle_error(ctx):
    print(f"Error in step {ctx['normal_error']['step']}: {ctx['normal_error']['error']}")

# Exit steps
async def log_transaction(ctx):
    # Log the transaction details
    print(f"Logged transaction with ID: {ctx['charge_credit_card']}")

async def cleanup(ctx):
    # Cleanup any resources or temporary files
    print("Resources cleaned up!")

# Create the workflow with initial context
wf = Workflow(ctx={"order_id": "order_001"})

# Add steps to the workflow
wf.add_step(validate_order, retries=2) # Retry twice if validation fails
wf.add_step(charge_credit_card, timeout=10) # Timeout after 10 seconds
wf.add_step(notify_warehouse)
wf.add_step(notify_shipping)
wf.add_parallel_steps([notify_user, send_email], name="notifications") # Parallel steps
wf.add_error_step(handle_error)
wf.add_exit_step(log_transaction)
wf.add_exit_step(cleanup)

# Run the workflow using asyncio.run
asyncio.run(wf.run())
```

In this scenario:

- We use retries for the order validation step. If there's a temporary issue with validation, it'll retry twice before failing.
- The credit card charge has a timeout to ensure the user isn't left waiting indefinitely.
- The user notification and email confirmation steps run in parallel to speed up the process.
- If any step fails, the error handler will provide information on the failed step.
- Exit steps ensure that the transaction is logged and any used resources are cleaned up, regardless of whether the workflow completed successfully or encountered an error.

This example showcases a combination of the features provided by the `Workflow` library in a real-world e-commerce order processing scenario.

## Organizing Multiple Workflows in a Project

---

Maintain a directory structure to keep workflows organized:

```
project_root/
|-- workflows/
|   |-- ecommerce/
|   |   |-- order_processing.py
|   |   |-- returns.py
|-- utilities/
|   |-- db_connector.py
|   |-- notifier.py
|-- main.py
```

- **Shared Utilities**: Place utilities or helper functions used across workflows in a `utilities` directory.
- **Workflow Dependencies**: Trigger or check the status of dependent workflows using shared context, callbacks, or database flags.
- **Configuration**: Use a configuration system for environment variables.
- **Logging**: Introduce logging for tracking and debugging.
- **Documentation**: Include docstrings outlining the purpose, prerequisites, input/output, and error handling for each workflow.
- **Testing**: Create test files for each workflow.
- **Versioning**: Implement versioning if workflows are subject to frequent changes.

## Dependency Injection in Workflows

---

1. **Define Interfaces for Dependencies**: These interfaces act as contracts.

```python
from abc import ABC, abstractmethod

class PaymentGateway(ABC):

    @abstractmethod
    async def charge(self, amount):
        pass

    @abstractmethod
    async def refund(self, amount):
        pass
```

2. **Provide Implementations**: Offer mock and real-world implementations.

```python
class MockPaymentGateway(PaymentGateway):

    async def charge(self, amount):
        print(f"Mock charged {amount}")
        return "Mock Transaction ID: 123456"

    async def refund(self, amount):
        print(f"Mock refunded {amount}")
        return "Mock Refund ID: 654321"

class RealPaymentGateway(PaymentGateway):

    async def charge(self, amount):
        # Real charge logic here
        pass

    async def refund(self, amount):
        # Real refund logic here
        pass
```

3. **Modify the Workflow to Accept Dependencies**: Accept dependencies as parameters during workflow initialization.

```python
class EcommerceWorkflow:

    def __init__(self, payment_gateway: PaymentGateway):
        self.wf = Workflow(ctx={"payment_gateway": payment_gateway, "order_id": "order_001"})

    async def charge_credit_card(self, ctx):
        transaction_id = await ctx["payment_gateway"].charge(100)
        print(f"Transaction ID: {transaction_id}")
        return transaction_id

    # ... other steps ...

    def run(self):
        # Add steps to the workflow...
        asyncio.run(self.wf.run())
```

4. **Inject the Dependencies**: Provide the required dependencies when initializing the workflow.

```python
# For testing
workflow = EcommerceWorkflow(payment_gateway=MockPaymentGateway())
workflow.run()

# For production
workflow = EcommerceWorkflow(payment_gateway=RealPaymentGateway())
workflow.run()
```

## Feedback and Contributions

---

Open issues or PRs on our GitHub repository. We value feedback and contributions!
