package org.springframework.samples.petclinic.owner;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;
import org.springframework.transaction.annotation.Transactional;

@SpringBootTest
@AutoConfigureMockMvc
@Transactional
public class OwnerControllerIntegrationTest {

  @Autowired private MockMvc mockMvc;

  @Autowired private OwnerRepository ownerRepository;

  @Test
  public void testOptimisticLockingFailureException() throws Exception {
    // Create and save an owner
    Owner owner = new Owner();
    owner.setFirstName("John");
    owner.setLastName("Doe");
    owner.setAddress("123 Test St");
    owner.setCity("Test City");
    owner.setTelephone("1234567890");
    ownerRepository.save(owner);

    final UUID ownerId = owner.getId();

    // Create a latch to synchronize threads
    CountDownLatch latch = new CountDownLatch(1);

    // Create an executor service to run concurrent requests
    ExecutorService executor = Executors.newFixedThreadPool(2);

    // Submit two concurrent update requests
    executor.submit(
        () -> {
          try {
            latch.await();
            mockMvc
                .perform(
                    MockMvcRequestBuilders.post("/owners/" + ownerId + "/edit")
                        .param("firstName", "John")
                        .param("lastName", "Doe")
                        .param("address", "456 New St")
                        .param("city", "New City")
                        .param("telephone", "0987654321"))
                .andExpect(status().is3xxRedirection())
                .andExpect(view().name("redirect:/owners/" + ownerId));
          } catch (Exception e) {
            e.printStackTrace();
          }
        });

    executor.submit(
        () -> {
          try {
            latch.await();
            mockMvc
                .perform(
                    MockMvcRequestBuilders.post("/owners/" + ownerId + "/edit")
                        .param("firstName", "John")
                        .param("lastName", "Doe")
                        .param("address", "789 Another St")
                        .param("city", "Another City")
                        .param("telephone", "1122334455"))
                .andExpect(status().is3xxRedirection())
                .andExpect(view().name("redirect:/owners/" + ownerId));
          } catch (Exception e) {
            e.printStackTrace();
          }
        });

    // Release the latch to allow both threads to proceed
    latch.countDown();

    // Wait for both threads to complete
    executor.shutdown();
    while (!executor.isTerminated()) {
      Thread.sleep(100);
    }

    // Verify the final state of the owner
    mockMvc
        .perform(MockMvcRequestBuilders.get("/owners/" + ownerId))
        .andExpect(status().isOk())
        .andExpect(view().name("owners/ownerDetails"))
        .andExpect(model().attributeExists("owner"));

    // You can add more specific assertions here to check the final state of the owner
  }
}
